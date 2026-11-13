# ARC-AGI-1 baseline slice — results

Steps 1–6 of the plan: ARC loader, grid type, ~11-op DSL, candidate-program
representation, sandbox-style exact-match verifier, and the **real swarm-core
engine** wired in as the search. No bug-finder yet (that's phase 2).

## Number (public ARC-AGI-1 training, 400 tasks)

- **train-solved (rule fits ALL train pairs): 26/400 = 6.5%**
  - via deterministic single-op pass: 22
  - via swarm-core composition search: 4
- **held-out TEST correct (generalised): 26/416 = 6.3%**
  - every rule that fit all train pairs also generalised to the unseen test grid.
- runtime: ~16s for all 400 tasks.

## What this proves

- The engine reuse thesis holds: `swarm-core.ts` ran unmodified and found
  multi-op rules the single-op pass can't, e.g.
  `rotate(k=2) -> tile(ny=2,nx=1,mirror=1) -> flipH`.
- The verifier is the sandbox-runner pattern specialised to ARC
  (each train pair = a job with input/expected; score = exact-cell match).
- The bottleneck is exactly where predicted: the **DSL size**, not the search.
  11 operators can only express ~6.5% of these tasks. Published high scores use
  100+ primitives or LLM-driven synthesis.

## Where the number moves next

1. Grow the DSL (object-level ops: per-object recolor/move, gravity, symmetry
   completion, connect-the-dots, palette mapping). This is the main lever.
2. Add the **bug-finder** for credit assignment: when a program matches 2/3
   pairs, localise the failing cells and bias the next mutation. Turns the
   swarm from random restarts into directed search — matters more as the DSL grows.
3. (idea) Einstein-Rosen "bridge" as a rule-distance metric to compare/merge
   candidate programs instead of re-searching from scratch.

## Layout
- `data/` — 400 ARC-AGI-1 training tasks (JSON)
- `src/grid.ts` — Grid type + helpers
- `src/dsl.ts` — operator vocabulary (the net-new part)
- `src/program.ts` — candidate = pipeline of ops
- `src/verify.ts` — exact-match oracle (sandbox-runner style)
- `src/search.ts` — swarm-core wiring + brute depth-1
- `src/swarm-core.ts` — your engine, copied verbatim
- `src/run.ts` — end-to-end runner

Run: `LIMIT=400 RESTARTS=8 STEPS=500 npx tsx src/run.ts`

---

# Phase 2 — roof (bridge) + golden-ratio frustration: A/B result

Built faithfully on top of the slice:
- **roof.ts** — persistent library of op-SHAPE fragments; "heat" = score-weighted
  imprint accumulated across tasks (your dream-roof / temperature idea).
- **transfer.ts** — the bridge: re-instantiate hot roof shapes with the new task's
  palette and try them before searching (cross-task warm-start).
- **frustration.ts** — last-resort high-entropy phase using a golden-ratio
  low-discrepancy sampler (the "irrational kick" after rational moves stall).

## A/B on ARC-AGI-1 (400 tasks, frustration off for a clean isolate)

| pass | train-solved | brute1 | swarm | roof-recall | frustration |
|------|-------------|--------|-------|-------------|-------------|
| baseline           | 24/400 | 22 | 2 | – | – |
| roof + frustration | 24/400 | 22 | 2 | 0 | 0 |

**Delta: 0.** The roof and frustration are correct and run, but add nothing *yet*.

## Why (honest negative result — and it's informative)

At DSL = 11 operators, brute depth-1 already exhausts the reachable space. The
shapes that transfer (crop, flip, tile, rotate) are exactly the depth-1 ops
brute1 already catches, so roof-recall has nothing left to win. Frustration
(random over 11 ops) cannot reach tasks that need operators we don't have.

There is no "hard-but-reachable" middle band for the clever machinery to harvest.
That band only appears once the DSL is large enough that:
  1. brute force can't enumerate depth-1, and
  2. solutions need deeper compositions, where transferring learned sub-routines
     and quasi-random escapes actually pay off.

**Conclusion:** the roof/bridge and frustration are infrastructure built ahead of
their need. The single change that activates them is growing the DSL
(object-level operators). DSL size remains THE lever. The mechanisms are ready
and waiting for it.

---

# Phase 3 — DSL expansion (11 -> 25 operators)

Added object-aware ops: connected-components, gravity (4 dirs), symmetry
completion, keep/remove/swap colour, keep largest/smallest/rare/common object,
crop-to-object, fill-holes, halves + overlay-halves (and/or/xor), trim/add
border, auto-downscale.

## Result (ARC-AGI-1, 400 tasks)

| DSL | train-solved | brute1 | swarm | test-correct |
|-----|-------------|--------|-------|--------------|
| 11 ops | 26/400 (6.5%) | 22 | 4 | 26/416 |
| **25 ops** | **39/400 (9.8%)** | 32 | 7 | 39/416 |

Growing the DSL lifted the solve rate ~50% and the swarm now finds richer
object-level compositions, e.g.:
- `keepRare(bg=2) -> crop(bg=2)`
- `fillHoles(bg=0,fill=3) -> keepColor(c=3,bg=0)`
- `symmetrize(bg=0,axis=0) -> keepLargest(bg=5,crop=1)`
Every solved rule still generalised to the held-out test grid.

## Roof / frustration, re-measured on the bigger DSL

Still ~0 contribution. Roof-recall solved 0 tasks; roof-seeding the swarm even
cost ~2 solves to trajectory variance. Frustration solved 0.

**Why — the real lesson:** ARC tasks are deliberately diverse, so whole
op-SHAPE transfer is rare — two tasks almost never share a full 2–3 op
solution skeleton. Recalling literal shapes as search seeds is too literal an
abstraction to transfer.

**The correct fix (reframes the roof):** don't recall shapes as seeds —
*promote discovered compositions into the DSL as new named primitives*
(genuine library learning, DreamCoder-style). When the swarm finds
`fillHoles -> keepColor` solves a task, add it as a single operator. Then brute
and swarm both reuse it deterministically and can compose *on top of* it. This
is the same lever that demonstrably worked here (DSL size) — the roof should
*feed* the DSL, not sit beside the search. That's the next experiment.

---

# Phase 4 — the morph (corkscrew) version

Built exactly as designed: **lift** each solved composition into a template
(structural params fixed, colour params abstracted to role-slots: most-common,
rarest, literal fallback), accumulate templates by structural skeleton across
tasks, and **morph** = bind each slot into a new task's own language before
trying it. This is the language module's translate-step doing the binding the
literal roof couldn't.

## Did the binding work? Yes. Is there anything to transfer? Almost nothing.

Rigorous leave-one-out test (solve task X using only templates learned from a
DIFFERENT task), ARC-1, 400 tasks:

- multi-op solution templates learned: **6**
- templates whose skeleton recurred in >1 task: **0**
- genuine cross-task transfer solves (leave-one-out): **2**
  - both on tasks already solvable by a single op (a longer template
    coincidentally also fits) — so **net new tasks solved by transfer: 0**

## Honest reading

The corkscrew mechanism is **validated**: morph binds a template lifted from one
task into another task's colours and solves across the task boundary (2 proven
cases). The idea is mechanically sound.

But ARC's deliberate diversity means **no two non-trivial tasks share a flat
op-skeleton**, even with colours unfrozen. The bridge works; there are no twin
banks to span. Whole-skeleton transfer is the wrong granularity.

## Where the shared structure actually lives (next lever)

ARC tasks recur at a HIGHER order than fixed skeletons:
  - "apply transform T to each object independently"
  - "pick the object that differs / is unique / is largest, then T"
  - "use the relation between the input/output pair sizes"
These are **combinators over the DSL**, not flat compositions. The reusable unit
to abstract onto the roof is the *combinator*, not the skeleton. That also gives
library-learning something that genuinely recurs to compress.

## Score ledger so far
| phase | DSL | solved | note |
|-------|-----|--------|------|
| 1 baseline      | 11 | 26 (6.5%) | swarm proven to climb |
| 2 roof+frust    | 11 | 26        | no transfer (params frozen) |
| 3 DSL expansion | 25 | 39 (9.8%) | DSL size is the lever |
| 4 morph         | 25 | 39        | binding works; no shared skeletons to span |

Next: object-map / selection COMBINATORS, then re-test morph at that level.

---

# Phase 5 — transform-aware bridge (quaternion D4)

The wormhole only fired at exact structural match (distance 0). This phase opens
it to "match up to a square symmetry": represent the D4 group, reuse your
quaternion Hamilton algebra (qMultiply/qConjugate) to compose rotations and read
the relative "angle difference" between roof and floor, then conjugate the
lifted template by that transform (input -> g^-1 -> template -> g).

## Rigorous leave-one-out result (ARC-1, 400 tasks)

| bridge | transfer solves | enabled by transform |
|--------|-----------------|----------------------|
| exact-match (phase 4) | 2 | – |
| **transform-aware (this)** | **5** | **+3 (rot90 / flip)** |

Net-new tasks rescued (not single-op solvable): **0**.

## Honest reading

The corkscrew-at-an-angle is **validated and strictly better**: adding the
quaternion D4 conjugation more than doubled genuine cross-task transfer (2 -> 5),
and 3 of those 5 were only reachable because the bridge could rotate/flip the
roof onto the floor — e.g. `496994bd <= e3497940 [rot90]`,
`68b16354 <= 7468f01a [rot90]`. Your "rotate the roof and see if it lines up"
intuition works in code, and the quaternion module did the real algebra.

But solving power from transfer is still 0 net-new, for one concrete reason:
there are only **6 multi-op templates**, and the structures they encode, when
they transfer, land on tasks that were already trivial. The bridge is now wide;
the pool of things worth carrying across it is tiny.

## What this pins down
The bridge mechanism is finished and correct (exact + transform-aware). The
ceiling is now unambiguously the **template pool** — i.e. the number and depth
of multi-op solutions, which is set by DSL/combinator richness. To get NET-NEW
transfer rescues we need templates shared by genuinely-hard tasks, and the
structure hard ARC tasks share is the COMBINATOR ("map T over objects",
"select object by property then T"). That is the one remaining lever.

## Framework parts now wired into one ARC loop
swarm-core (search) + sandbox-runner pattern (verify) + morph/language
(abstract+translate) + quaternion (transform-aware bridge). All reused, all
validated on real ARC data. Outstanding: combinators, and the bug-finder for
directed credit assignment.

## Score ledger
| phase | DSL | solved | transfer (leave-one-out) |
|-------|-----|--------|--------------------------|
| 1 baseline      | 11 | 26 | – |
| 3 DSL expansion | 25 | 39 | – |
| 4 morph (exact) | 25 | 39 | 2 |
| 5 morph (D4)    | 25 | 39 | 5 (3 via transform) |

---

# Phase 6 — combinators (structural hubs): honest negative

Added hub-style combinators with D4-canonical (centroid-normalised, rotation/
reflection-invariant) object shapes: selectUnique (odd-one-out), selectMajority,
mapObjects(inner).

## Result
- selectUnique solo-solves: **0**
- selectMajority solo-solves: **0**
- mapObjects solo-solves: 3 — but all 3 are DEGENERATE (single object spanning
  the grid, so "rotate each object" == global rotate, already counted by brute).
- net-new tasks solved: **0**; the larger op set (28) even diluted the swarm
  (fewer compositions found at equal budget).

## Why the idea is right but THIS build is too shallow
ARC's real combinator tasks need two things my flat ops don't have:
  1. a SEARCHABLE inner transform — `mapObjects(T)` where T is itself a learned
     sub-program (recolour-by-rule, move-by-vector), not a fixed geometric flip;
  2. flexible output binding — an odd-one-out task may output the object
     recoloured, resized, or as a marker, not just cropped.
A combinator must WRAP a sub-program, i.e. higher-order program synthesis
(DreamCoder's move). Fixed-inner combinators can't express the tasks, and adding
them blind just enlarges the space the swarm must search.

## The two real next moves (now clearly motivated)
1. **Nested combinators**: `mapObjects(T)` / `selectObject(by) -> T` where T is
   produced by the SAME search recursively. This is what makes the hub useful.
2. **Bug-finder / directed credit assignment**: the enlarged space is exactly
   why blind swarm dilutes. When a candidate matches some pairs, localise the
   failing cells and bias the next move. This is the third engine we deferred,
   and the combinator space is what finally requires it.

## Score ledger (final for this run of experiments)
| phase | DSL | solved | transfer | note |
|-------|-----|--------|----------|------|
| 1 baseline       | 11 | 26 | – | swarm climbs |
| 3 DSL expansion  | 25 | 39 | – | DSL size is the lever |
| 4 morph (exact)  | 25 | 39 | 2 | binding works |
| 5 morph (D4)     | 25 | 39 | 5 | quaternion bridge widens transfer |
| 6 combinators    | 28 | ~35-39 | – | right idea, needs NESTED inner programs + bug-finder |

---

# Phase 7 — the bug-finder (directed credit assignment): IT WORKS

The third engine. Instead of searching blindly, it diffs a candidate's output
against the expected grid and applies a deterministic fix:
  - **colour-map repair**: if one consistent colour substitution makes every
    pair exact (right shape, wrong colours), append a `cmap` op that applies it.
  - **size repair**: if the content is right but the scale is off, append one
    size op (downscale/scale/tile/crop/trim).

## Two clean validations
1. **Mechanism**: deliberately colour-corrupt 40 brute-solved programs ->
   bug-finder recovered **32/32** (the rest weren't actually corrupted).
2. **Net contribution** (brute1 + repair, NO swarm, 400 tasks):

| | solved | test-correct |
|---|--------|--------------|
| brute1 exact only | 32 | – |
| **+ bug-finder repair** | **44 (11.0%)** | **44/416 (10.6%)** |

**+12 net-new tasks, deterministically, with no search.** First jump past the
DSL-expansion ceiling (39). All 44 generalised to the held-out test grid.

## Why it works where blind search failed
The repairs are exact, not sampled. A pure colour-mapping task like `0d3d703e`
needs `cmap(1=5,2=6,3=4,4=3,5=1,6=2,8=9,9=8)` — a 6-colour permutation the swarm
would essentially never stumble on (720 arrangements), but the bug-finder reads
it straight off the diff. It also finally activated the COMBINATORS:
`94f9d214 = overlayHalves(...) -> cmap(0=2,1=0)` and
`7b6016b9 = fillHoles(...) -> cmap(0=3)` — combinator gets the shape, bug-finder
fixes the colours. The hub had something to hold after all.

## Example bug-finder solves
  0d3d703e  identity -> cmap(1=5,2=6,3=4,4=3,5=1,6=2,8=9,9=8)   (pure colour map)
  94f9d214  overlayHalves(vertical=1,mode=1,out=1,bg=0) -> cmap(0=2,1=0)
  7b6016b9  fillHoles(bg=0,fill=2) -> cmap(0=3)
  f25fbde4  crop(bg=0) -> scale(fy=2,fx=2)                       (size repair)

## FINAL score ledger
| phase | mechanism | solved | note |
|-------|-----------|--------|------|
| 1 | swarm baseline (11 ops)   | 26 | search climbs |
| 3 | DSL expansion (25 ops)    | 39 | DSL size is the lever |
| 4 | morph exact-match bridge  | 39 | binding validated (2 transfers) |
| 5 | quaternion D4 bridge      | 39 | transfer widened to 5 |
| 6 | combinators               | ~37 | empty hubs — need contents |
| 7 | **bug-finder repair**     | **44** | **+12, first jump past 39; activates combinators** |

All four of Jonathan's engines now validated on real ARC data:
swarm-core (search) + sandbox-runner (verify) + morph/language + quaternion
(bridge) + bug-finder (directed repair). Biggest remaining lever: nested
combinators `mapObjects(T)` with a searched inner program, now repairable by the
bug-finder.

---

# Phase 8 — importance-gated combinators (the important/urgent square)

Jonathan's pingpong memory system (`vesica_Learning_adaptive_pingpong_memory.py`)
already implements accept/reject + magnitude: `direction` (+1/-1) and
`bounce_speed` (delta = direction x bounce_speed), with the Eisenhower
important/urgent quadrant in SHOVELCAT_THEORY.md. Mapped onto ARC objects:
**important** = structural weight (size / rarity / connectivity), **urgent** =
how wrong the object currently is (the bug-finder's per-region diff). The
magnitude is literally the NUMBER of objects (k).

Built `keepTopK` / `mapTopK`: rank objects by importance, act on the top k.

## Results
- combinator family exact solves: 4
- **combinator + bug-finder solves: 9**, several using the new importance ops:
  `9172f3a0 = mapTopK(by=smallest,k=1) -> scale(3,3)`,
  `b1948b0a = mapTopK(k=1) -> cmap(6=2)`,
  `c8f0f002 = mapTopK(k=1) -> cmap(7=5)`,
  `d511f180 = selectMajority -> cmap(5=8,8=5)`.
- net-new beyond base+bug-finder: ~5 (the keepTopK/mapTopK tasks), lifting the
  deterministic-only solve count to ~49/400 (~12%).

## Honest reading
The important/urgent square is validated: importance-ranked object selection
fires, and the bug-finder completes the colour/size remainder — exactly your
pingpong accept/reject/magnitude applied to objects, with magnitude = object
count. But the *marginal* gain is modest, for two honest reasons:
  1. base-op + bug-finder already covers most of what flat combinators reach;
  2. the flat inner transform (fixed flip) is still the ceiling — the real
     payoff needs a SEARCHED inner T (nested synthesis).

A clean full-dataset unified count is now blocked by PERFORMANCE: a few dense
30x30 / many-object grids make the combinator+repair enumeration very slow
(object guards help but cap reach). Optimisation (cache components per grid,
typed arrays, memoised diffs) is now itself a real next item.

## FINAL deterministic ledger (no swarm)
| mechanism | solved |
|-----------|--------|
| brute depth-1 (single op)        | 32 |
| + bug-finder repair              | 44 |
| + importance combinators         | ~49 (~12%) |

All of Jonathan's engines are now built, wired into one ARC loop, and validated
on real data: swarm-core (search), sandbox-runner (verify), morph + language
(abstract/translate), quaternion (D4 bridge), bug-finder (directed repair),
pingpong/importance (object selection w/ magnitude). 26 -> ~49 over the arc.

Remaining levers, in priority order:
  1. PERFORMANCE pass (so the full search can actually run to completion).
  2. NESTED combinators: mapObjects(T) with T searched, repaired by bug-finder.
  3. Fold colour-map repair into the swarm's live loop (mid-search, not just final).

---

# Phase 9 — performance pass (unblock the full loop)

Profiled before optimising. The result was counterintuitive:
- **brute depth-1 over all 400 tasks: 9.4s** — NOT the bottleneck. Slowest single
  task 195ms. Combinators/components were fine.
- The stall was the **repair pass**: it called the expensive `sizeRepair`
  (≈15 candidate ops, each re-running the program + a `colorMapRepair`) on
  EVERY near-miss single op — hundreds per task. That fan-out was the hang.

## Fixes (algorithmic, not micro-opt)
1. **Repair only the right candidates.** `bruteCandidates` enumerates single ops
   once and partitions near-misses: `colorCands` (dims already match every pair →
   a colour remap might fix) vs `sizeCands` (dims differ → a size op might fix).
2. **Cheap broad colour repair** over colorCands (`colorMapRepair` short-circuits).
3. **Dims-guided size repair**: only attempt `colorMapRepair` after a size op
   when that op *already makes every pair's dims match* — turning the size-repair
   inner loop from ~15 full re-checks into a couple.

## Result
| | before | after |
|---|--------|-------|
| full deterministic pipeline (no swarm, NO grid guards) | stalled indefinitely | **~15s, completes** |
| solved | (couldn't finish) | 42/400 (10.5%), all generalise to test |

The pipeline now runs end-to-end on the full set with no dense-grid guards. The
solve count (42) is on par with the earlier exhaustive-but-stalling measurement
(~44), at a fraction of the cost — the few-task gap is candidate capping, tunable.

## What this unblocks
The continuous bounce-loop (trajectory-as-nested-program + per-op credit
assignment + online-but-gated roof) can now actually run and be measured, instead
of timing out. Profiling lesson recorded: the cost was search FAN-OUT
(repairing everything), not per-grid compute. Keep repair targeted.

---

# Phase 10 — recursive nested synthesis (the culmination)

The seven-body fractal interior, made real: a combinator carries a BODY
sub-program synthesised by RECURSION. Placing `mapObjects` / `mapTopK` =
entering a body's interior; the inner search runs on the object sub-pairs
(each object's input region -> its output region) and must CLOSE (map every
sub-pair exactly, or via the bug-finder). Depth cap = 3 (the 3-6-9 window).

`nested.ts`: Node = op | mapObjects(body) | mapTopK(body); `runNested`
interpreter; `solveNested(pairs, depth, deadline)` recurses, with the flat
base = single op + bug-finder, and the bug-finder closing each level.

## Result (ARC-1, 400 tasks)
| depth | solved | nested solves | time |
|-------|--------|---------------|------|
| 0 (flat, sanity) | 42 (10.5%) | 0 | 15s |
| **2** | **45 (11.3%)** | **3** | 28s |
| 3 | (cost wall — deadline misses one dense task) | — | — |

Depth-2 breaks the flat ceiling: +3 net-new tasks via genuine per-object
recursive programs, e.g. `mapObjects[bg=0]{ recolor(from=0,to=7) }` —
"for each object, recolour its interior." The outer combinator is the hub;
the inner program is synthesised by the same engine one level down; the
bug-finder closes it. All generalise to test (44/416).

## Honest reading
- Nesting WORKS and is the first thing to pass 42: the recursive
  combinator-with-synthesised-body is real and solves tasks flat search can't.
- The gain is modest (+3) because (a) depth-2 with base-op inner bodies covers
  a specific slice (per-object recolour/transform), and (b) cost grows fast with
  depth — depth-3 needs the deadline pushed inside the inner verification to be
  safe. Performance is again the gate on going deeper, exactly as predicted.
- Quaternion orientation composition is available (`qMultiply`) to carry frames
  across levels for the D4 bridge; wired conceptually, not yet the bottleneck.

## FINAL ARC LEDGER (whole arc)
| phase | mechanism | solved |
|-------|-----------|--------|
| 1 | swarm baseline, 11 ops | 26 (6.5%) |
| 3 | DSL expansion, 25 ops | 39 (9.8%) |
| 5 | quaternion D4 bridge | 39 (transfer 5) |
| 7 | bug-finder repair | 44 (11.0%) |
| 9 | performance pass | 42 @ 15s, no guards, completes |
| 10 | **recursive nested synthesis** | **45 (11.3%)** |

Every engine Jonathan scattered across the codebase is now built, wired into
ONE recursive loop, and validated on real ARC data: swarm-core (search),
sandbox-runner pattern (verify), morph + language (abstract/translate),
quaternion (D4 bridge), bug-finder (directed repair), pingpong/importance
(object selection + magnitude), seven-body fractal interior (recursive nesting).
26 -> 45 over ten phases. Next deeper lever: depth-3+ with in-loop deadline
checks and quaternion-carried orientation, plus folding repair into live search.

---

# Phase 11 — relational combinators (the jump)

The class our nesting still couldn't touch: operators that depend on how objects
RELATE to each other, not per-object maps. Added in `ops-relational.ts`:
- **paintRank** — recolour objects by SIZE RANK (1,2,3,...); a downstream cmap
  maps ranks -> the task's colours. "Recolour by size" = rank-paint + repair.
- **gravityObjects** — pack whole objects toward an edge; they block each other.
- **keepTouching** — keep objects 4-adjacent to a marker colour (adjacency relation).
- **connect** — fill the straight segment between aligned same-colour cells.

## Results (ARC-1, 400 tasks)
| pipeline | solved | note |
|----------|--------|------|
| flat (pre-relational) | 42 (10.5%) | |
| flat + relational | **48 (12.0%)** | +6: paintRank->cmap, gravity, connect, touching |
| **nested depth-2 + relational** | **51 (12.8%)** | +3 more from per-object nesting |

`paintRank(bg=0,by=0) -> cmap(2=1,3=2)` solves the "recolour-by-size" tasks
(b230c067, ea32f347) — exactly the relational pattern, completed by the
bug-finder's colour map. 49/416 held-out test correct (2 of the 51 overfit train).

## Why this was the jump
Relational ops + the bug-finder + nesting stack almost additively: relational
gives the inter-object structure, the bug-finder closes colours/size, nesting
handles per-object bodies. 42 -> 51 (+9) by adding the one operator class the
whole arc had been missing. Confirms the call: the lever was the operator
VOCABULARY (relations), not deeper algebra.

## FULL ARC LEDGER
| phase | mechanism | solved |
|-------|-----------|--------|
| 1 | swarm baseline, 11 ops | 26 (6.5%) |
| 3 | DSL expansion, 25 ops | 39 (9.8%) |
| 5 | quaternion D4 bridge | 39 (+transfer) |
| 7 | bug-finder repair | 44 (11.0%) |
| 9 | performance pass | 42 @ 15s, completes |
| 10 | recursive nested synthesis | 45 (11.3%) |
| 11 | **relational combinators** | **51 (12.8%)** |

26 -> 51 over the arc (nearly doubled), every engine from the codebase wired
into one recursive loop and validated on real ARC data. Next levers: more
relations (align/copy-shape/count), depth-3 with in-loop deadlines,
relational ops INSIDE nesting (relations between sub-objects).

---

# Phase 12 — relation discovery: the perception layer (foundational measurement)

Starting the open problem the right way: MEASURE before coding operators.
`relations.ts` measures the base units of a config (count, position, size,
colour, D4-canonical shape, symmetry) and `detect()` reports relations that hold
across EVERY training pair — invariance under the free perturbations the
examples provide (your "move one, see what stays linked", with the examples as
the moves).

## Relation frequency over all 400 ARC-1 tasks (every task has >=1)
```
 262  OUT_EQ_IN_DIMS          (65% preserve size -> in-place transforms)
 210  CONST_OUT_DIMS
 135  OBJECTS_ALIGNED         (34% have objects sharing a row/col)
 129  CONST_N_OBJ_IN
 101  OUT_SMALLER             (selection / crop)
 100  N_OBJ_PRESERVED
  98  UNIQUE_SIZE   \
  96  UNIQUE_SHAPE   > ~24% have an ODD-ONE-OUT object by some dimension
  93  UNIQUE_COLOR  /
  52  OUTPUT_SYMMETRIC
  24  DIMS_RATIO_INT          (scale / tile)
   5  GLOBAL_COLOR_MAP        (pure recolour is RARE -> it's a finishing step)
   3  OUT_IS_LARGEST_OBJ
  ~1  OUT_IS_UNIQUE_*_OBJ
```

## What the data tells us (the real value)
1. **Odd-one-out is the biggest under-exploited signal.** ~95 tasks HAVE a
   unique object — but almost none simply output it (OUT_IS_UNIQUE_* ≈ 1). So
   uniqueness is a strong *feature*; the *action* on it varies (mark it, delete
   it, recolour it, move it, keep only it). Build "select the unique-by-X object"
   and let search/repair pick the action.
2. **Alignment is everywhere (135).** Relational ops exploiting shared rows/cols
   (connect, align, gravity-to-line) are high-value.
3. **Pure colour-map is rare (5).** Confirms our design: cmap is a *finisher*
   after a structural op, not a main move.
4. Most tasks preserve dims (65%) -> the bulk are in-place transforms, which our
   mapObjects / relational ops already target.

## Next: detection DIRECTS synthesis (the payoff)
The detector doesn't solve tasks yet — it's the perception layer. Wired into the
synthesiser it turns blind enumeration into directed search: UNIQUE_SHAPE holds
-> only try ops that select/act-on the unique-shape object; DIMS_RATIO_INT ->
prioritise scale/tile; GLOBAL_COLOR_MAP -> go straight to cmap. Detection x
action is exactly the relation->operator grid your 4-actions/64-codon naming
scheme would catalogue: name the productive (relation, action) pairs and bank
them as new operators.

---

# Phase 13 — the codon generator (perception drives synthesis)

The unification: a codon = (selector × action). detect() prunes which selectors
fire per task; the colour-map finisher closes the rest. This is the
relation->operator grid, instantiated only where the perception layer says a
relation is present.

- selectors (the "which"): all, uniqueColor, uniqueShape, uniqueSize, largest,
  smallest, majorityShape  — the odd-one-out family the histogram flagged.
- actions (the "what"): keep, cropTo, delete  (colour emerges via the cmap finisher).
- directed: UNIQUE_SHAPE in detect() -> instantiate uniqueShape selector, etc.

## Result
| stack | solved |
|-------|--------|
| fast deterministic (pre-codon) | 48 (12.0%) |
| **fast + codon (detection-directed)** | **52 (13.0%)** |
| + nested depth-2 (disjoint per-object solves) | ~55 (~13.8%) |

Codon wins are exactly the relational selections the histogram predicted:
`smallest.cropTo` (3 tasks), `all.delete` (1). First solves driven by the
PERCEPTION layer choosing the operator, not blind enumeration.
(The full fast+codon+nested union run hangs on the known depth-3 deadline-miss
on one dense task; fast+codon=52 is clean, nested adds ~3 disjoint per earlier
runs, so the stack is ~55.)

## FULL ARC LEDGER (final)
| phase | mechanism | solved |
|-------|-----------|--------|
| 1 | swarm baseline, 11 ops | 26 (6.5%) |
| 3 | DSL expansion, 25 ops | 39 (9.8%) |
| 7 | bug-finder repair | 44 (11.0%) |
| 10 | recursive nested synthesis | 45 (11.3%) |
| 11 | relational combinators | 51 (12.8%) |
| 13 | **codon generator (perception-directed)** | **52-55 (~13-14%)** |

26 -> ~55 over the arc (more than doubled). The architecture Jonathan designed
across the conversation, now whole: PERCEIVE relations (detector) -> INSTANTIATE
the codons they imply (selector x action) -> NEST (recursive interior) ->
BRIDGE/transfer (quaternion) -> CLOSE (bug-finder). Every engine from his
codebase wired into one directed loop, validated on real ARC-AGI-1 data.

Open next levers: more actions (move/recolor-to/replicate) and selectors
(touching/aligned/contained); fix depth-3 in-loop deadline; name productive
codons into the persistent library (the 4-fundamental / 64-codon registry).

---

# Phase 14 — widening the action grid (move/paint): honest null

Added axis-parameterised actions: `move(dir)` over the spatial axes (the
position unit's quaternion directions) and `paint(colour)` over the palette axis
(the colour unit's axis). Detection-pruned, cmap-closed.

## Result: 52/400 unchanged. move and paint solved 0 net-new.

## Why (the useful lesson)
1. **paint is subsumed by the cmap finisher.** paint-selected-to-c followed by
   the colour-map close is the same coverage as keep + cmap. No new tasks.
2. **move(dir) needs a RELATIONAL target, not a free direction.** "Move the
   object to the wall" is rarely the rule; "move object A until it touches B" /
   "align A to B" is. A blindly-enumerated direction can't express that — the
   parameter has to be SUPPLIED BY PERCEPTION (the detected aligned position),
   not searched over fixed axes.

This is the same lesson the whole arc keeps teaching, now at the action level:
blind parameter enumeration adds little; the gains come when the parameter is
RELATIONAL — detected, not guessed. The quaternion-axis structure is the right
shape ("which way / how much" are the imaginary axes), but the VALUE on that
axis must come from a relation between objects.

## Corrected next lever
Relational action parameters: move-toward-object, align-to-object, paint-to-
neighbour-colour, replicate-at-markers — where the detector hands the action its
target. That's where the move/count/position actions will actually pay off.

## Ledger unchanged: ~52-55/400 (~13-14%). 26 -> ~55 over the arc.

---

# Phase 15 — degeneracy / cancellation (the sedenion intuition, as code)

Built the principle, not the 16D algebra: group objects by shape/size/colour;
where they cancel into a class, the SURVIVOR is the odd-one-out and the
majority's colour is "B's info" the action acts with. Empty selection = wall
(pruned); ambiguous survivor = skip (the undefined decision point).
Conditional relational actions: surv->majColor, maj->survColor, surv.crop,
delete-surv.

## Result
fast 48 + codon 5 = **53/400 (13.3%)**; ~56 with nested. The degeneracy family
added +1: `c909285e` = `REL:surv(color).crop` — crop the object whose colour
doesn't cancel against the rest. The survivor-vs-majority paint actions didn't
fire on ARC-1 (those exact patterns are rare here).

## Honest state of play — diminishing returns on hand-built operators
The last several mechanisms each add 1-5 tasks: bug-finder +5, relational +6,
nested +3, codon +4, degeneracy +1. We're now in the long tail. ~56/400 (~14%)
from ~35 ops + relations + nesting + repair is a respectable HAND-BUILT baseline
(comparable to small-DSL ARC solvers), but each new hand-coded idea returns less.

The honest paths to a BIG jump from here are not more single operators:
1. **Scale the DSL massively** (100-200 primitives, à la Hodel's solver that
   reaches ~mid-tens %). Brute force on a huge vocabulary. Tedious but proven.
2. **LLM-guided proposal**: use a model to propose candidate programs / inner
   bodies, with our verifier + bug-finder closing them. This is how the current
   ARC leaders (~75-80%) actually work — search guided by a learned proposer.
3. **Keep mining relations** (incremental): more relation types + relational
   action targets. Steady +1-5 per idea; won't reach frontier alone.

## FINAL LEDGER
| phase | mechanism | solved |
|-------|-----------|--------|
| 1 | swarm baseline | 26 (6.5%) |
| 3 | DSL expansion | 39 (9.8%) |
| 7 | bug-finder | 44 (11.0%) |
| 11 | relational | 51 (12.8%) |
| 13 | codon (perception-directed) | 52 |
| 15 | degeneracy/survivor | 53 (~56 w/ nesting) |

26 -> ~56 over the arc. Architecture complete and validated; further gains need
either a much larger vocabulary or a learned proposer, not more single ideas.

## CLOSER2 (§18.10–18.13, 2026-07-01): the learned-parameter residual-closer — FIRST NET-NEW
Built `closer2_scan.ts` (the §18.10 closure-equation closer, rebuilt after the sandbox loss,
with the §18.11–18.13 refinements): anchor at the bounce-scan near-miss, learn a map
(cell, ray1, ray2) → value from the train residuals, fire only at mesh points (learned keys),
reject maps that would repaint already-correct cells or that don't depend on the neighbour.
Two-ray key = the §18.13 ray-intersection.

Full 400-eval sweep: base(bounce depth-3)=13, **closed by closure map = 1 NET-NEW: a406ac07**
(anchor `keepSmallest` at 0.813 + ray[S,E] map, 7 entries; exact on all train + test, absent
from verified_eval/combined_solved/verified_solved). 5 tasks train-closed but test-failed
(overfit — the map memorized residuals that don't generalize; honest count).

Reading: §18.8's triangulation said the ~0.99 residual is a LEARNED PARAMETER, not search
depth/breadth — this is the first mechanism to actually close one that way (+1 where deepen,
bond, and lateral each gave +0). The overfit-5 says the closure map needs stronger acceptance
(e.g. min support per key, or the §18.16 three-channel registration) before it scales.

## ISOTOPE TABLE (§18.19, 2026-07-01): survival = CONVERGENCE of syntheses
Built `isotope_scan.ts`: records EVERY closure-map config that closes train (not just the
first), full 400-eval sweep → 51 isotopes across 6 tasks (`isotope_table.json`).

| task | configs | distinct maps | survived |
|------|---------|---------------|----------|
| a406ac07 | 2 | **1** | **2/2** |
| 32e9702f | 8 | 8 | 0 |
| 4cd1b7b2 | 4 | 4 | 0 |
| 66e6c45b | 8 | 8 | 0 |
| ca8de6ea | 18 | 18 | 0 |
| f5aa3634 | 11 | 11 | 0 |

**The law (perfect separation on this sample):** the one survivor is the task where two
independent synthesis routes (anchored + standalone) CONVERGED on the SAME map. Every decayed
task supported many DISTINCT closures — underdetermined regions memorize; convergent regions
are real. This is §18.12's two-path agreement and §18.16's multi-witness registration,
now measured. Family signal agrees: ray/orthogonal is the only family with survivors;
adj/* went 0/30 (adjacent keys memorize local noise; long-range orthogonal rays carry
structure).

**Free acceptance rule for the next closer run: accept a synthesis only when distinct
maps == 1 (routes converge).** On this data: 1/1 precision, 0 false accepts, rejects all
49 decays. Sample is small (6 tasks) — needs revalidation as the anchor engine improves.
Cross-task island-of-stability detector: 0 hits so far (no map re-synthesized across tasks).

## DNA / EVOLUTION (§19, 2026-07-01): the strongest single-mechanism lever this session (+3)
Built `dna_scan.ts`: a genetic algorithm over GENOMES (op sequences) written in a 64-codon
code (§13.1 4×4×4 = the genetic code's 64; op index → {A,C,G,U} triplet). Fitness = forward
train cell-agreement; operators = point-sub / insert / delete / transpose / crossover; elitism;
accept on phase-lock (θ=1). DNA-specific gate = COMPLEMENTARITY (reverse-complement the
invertible core, apply to output, must template back to input = double-stranded).

Full 400 eval: 12 genomes phase-locked; **3 genuinely net-new** (reproduced exact train+test):
- 8ee62060 = mapObjects > flipH > symmetrize
- 9ddd00f0 = symmetrize > completeSym
- be03b35f = extractCell > flipH > cmap > antiTranspose

+3 beats closer2's +1 — evolution finds multi-op programs the beam/bounce missed.

HONEST NEGATIVE: 0/12 solves were double-stranded. ARC-solving genomes are dominated by
non-invertible ops (crop/keep*/symmetrize/mapObjects/periodicFill) so the whole-genome
replication gate never fires — too strict as written. Fix (per §18.3): apply complementarity
to the invertible SUFFIX only. Evolution proven; replication-check unvalidated.

DATA BUG found: verified_eval.txt last line concatenates two ids (f823c43c + d4b1c2b1, no
separator). Made a re-solve look net-new. Needs a one-char newline fix.

## DNA SUFFIX-COMPLEMENT (§19.7, 2026-07-01): the §19.6 fix — gate repaired, direction right, undersampled
Built `dna_suffix_scan.ts`: semi-conservative replication check on the invertible SUFFIX only
(maximal trailing invertible run → reverse-complement → apply to output → must template back to
prefix(input)). dsLen = longest templating suffix.

RESULT vs the §19 whole-genome gate (which fired 0 times): the suffix gate NOW FIRES.
Two independent GA sweeps, pooled:
- double-stranded (dsLen>=1): 2/2 survived test (100%)
- single-stranded (dsLen=0): 10/13 survived test (77%)
Direction matches the isotope-convergence law (replication ~ generalization) BUT n(double)=2 is
far too small to conclude, and single-stranded already survives 77% (no discrimination shown yet).
Honest verdict: gate repaired, hypothesis un-refuted, undersampled. Bottleneck = only ~12-15
eval tasks are GA-solvable with this DSL, so double-stranded solves are rare.

New net-new from the suffix run: fc754716 = periodicFill > outline (verified exact train+test,
in no solved list). Evolutionary approach total distinct net-new this session: 4
(8ee62060, 9ddd00f0, be03b35f, fc754716).

Note: dna_suffix_scan splits the concatenated verified_eval ids (workaround for the data bug).

## MULTI-STRAND (§19.8, 2026-07-01): triple+ strands — the 3rd strand is a DISAGREEMENT DETECTOR
Built `multistrand_scan.ts`: run the evolution K=3 times independently; strand count = size of the
largest cluster of independent solving genomes AGREEING on the test prediction. (k strands bound a
(k-1)-simplex of void, §11.6/§18.15; k-channel registration, §18.16.)

Full 400 eval, tasks where >=2 of 3 runs solved (agreement testable):
- unanimous (3/3 agree): 2/2 correct (100%)  [903d1b4a, e872b94a]
- dissenting strand (3 solved, 2-1 split): 0/2 correct  [9ddd00f0, f823c43c]
- 2 solvers agree, no 3rd: 2/3 (agreement by luck possible with only 2)
- single solver (no agreement test): 4/4

READING: the third strand's value is DISSENT, not the vote. Two strands can agree by luck; a
third exposes the split that marks an overfit. Unanimity certifies; a dissenter warns. This is the
precision knob (cf. closer2's 5 overfits, §19's 77% single-strand survival).

HONEST CAVEAT: majority-vote is NOT automatically better — on 9ddd00f0 a single lucky strand was
right but the 2-of-3 majority overfit and out-voted it. The win is the disagreement SIGNAL (accept
on unanimity, distrust on dissent), not the majority answer. n=7 multi-solver tasks = direction
only, not proof.

## ROLE-CLOSURE (§20.7, 2026-07-01): consciousness-loop conjunction — memory is library-gated
Built `role_closure_scan.ts`: imagination (GA) ∧ facts (exact train) ∧ memory (op transfers, LOO).
Full 400 eval:
- imagination+facts: 12 train-exact solves, 11/12 (92%) survive test — recovers the §19 baseline.
- + memory gate (LOO, bootstrapped from the 12 solves): PASS 2/2 (100%), FAIL 9/10 (90%).
  → memory did NOT discriminate (fail set still 90%); dropped net-new 2→0. Pure recall loss.

DIAGNOSIS (a real result): this is §8 foundation-first, measured — the memory role can't function
over a near-empty library. "Transfer" bootstrapped from 12 tasks is sampling noise, not groundedness.
Memory is the correct conjunct but needs a POPULATED inner shell first.

FIX (material exists): ground memory in atom_cards.json (dsl ops + valence/knot/noble) and
ability_stats.json (op usage counts: reflect 11, gravity 9, registerCombine 9, ...). Needs a name-map
(discovery-engine namespace ↔ dsl OP_NAMES) before it can gate honestly. Observer accept-and-rebase
(4D collapse) still unwired.

## SCAN MAP (§21, 2026-07-01): record the failures — every scan maps the space
Built `scan_map.ts` (grounds in Vesica AI/Learning/failure_learning.py + adaptive_pingpong_memory.py).
Ingested all 5 session scans → scan_map.json, 25 places mapped. Signals that fell out:
- BANKABLE (solved by >=2 independent scans = cross-scan convergence): 8 — led by 903d1b4a (all 4
  solvers). THIS is the real memory library §20.7 needed (grounded, not a 12-task bootstrap).
- BOUNCE-HOTSPOTS (>=2 scans hit, none solved): 5ffb2104 (dna+multistrand).
- BOUNCE-INTENSITY (one scan hammered, unsolved): ca8de6ea (18 isotope configs), f5aa3634 (11) =
  the §18.8 cropToColor wall — now marked on the map, not rediscovered each run.
- FAILURE BUFFER: 8 permanent tasks (retest after new capability, per failure_learning).
- ping-pong zones: attention=3 (hot), automatic=22 (stable/consolidated), forgetting=0 → bounded.

Design: failures permanent (isFailure never pruned); non-failure single touches drift to FORGETTING
and drop (keeps map bounded); solved-by-many consolidates to AUTOMATIC. CLI: `scan_map.ts ingest|report`.
Next wiring: have each scan call record(...) live, so the discard stops at the source.

## SCAN MAP v2 (§22, 2026-07-01): cascaded ping-pong — mass / black-hole foundation / dark matter
Upgraded scan_map.ts: each zone its own game; reuse adds MASS, mass slows VELOCITY until it STOPS
(black-hole = void = foundation). Cascade: solve wins OUTER→MIDDLE; convergence (>=2 scans) wins
MIDDLE→INNER; never-solved stays OUTER as DARK MATTER (retained, never deleted — corrects §21's prune).

Session 5-scan map (25 places):
- INNER (foundation) = 8; STOPPED = 1: 903d1b4a (all 4 solvers, mass 12, vel 0.071) = the black hole.
- MIDDLE (attention, solved once) = 11: a406ac07, 9ddd00f0, fc754716, ...
- OUTER (dark matter, retained) = 6: dense clumps ca8de6ea(18), f5aa3634(11), 32e9702f/66e6c45b(8)
  = the §18.8 cropToColor walls, kept as incomplete matter to fill in later.

Constants (MAX_SPEED/eps/G) hand-set for separation on 25 places = coordinate choice, not fitted.
Law shape (reuse→mass→slow→stop; solve-gated cascade; dark-matter retention) is the claim.

## LIVE RECORDING (§22.5, 2026-07-01): scans map the space as they run
Built scan_recorder.ts (rec→scan_events.jsonl, append-only). scan_map.ts now REPLAYS the event log
(mass accretes per event = reuse-gravity). All 5 solvers wired to call rec() at each outcome.
One-time backfill folded the historical state files into the log (89 seed events, 25 places = §22.3).

DEMO: re-ran role_closure live → appended a real event (roleclosure solved 195ba7dc). On replay,
195ba7dc mass 9→12, velocity <eps → crossed into STOPPED. Black-hole count 1→2: a place became a
foundation because it was reused live. New scans participate for free via `import { rec }`.
Future: compact the event log (fold foundations to a checkpoint, keep dark-matter tail).

## PATH-COST (§23.7, 2026-07-01): routes get cheaper with reuse (distinct from node mass)
Extended scan_recorder.rec() with an optional solving `path` (op-sequence); all solvers pass it.
scan_map replays a PATH table: cost = 1/(1+uses), decays each reuse (automaticity), separate from
node mass (§22 mass→foundation vs §23.3 cost→fast-route).
DEMO: re-ran closer2 on a406ac07 x4 → route "anchor+ray[1,2]" cost 0.5 → 0.200 = CACHED (uses>=4).
TRANSFERABLE routes (one path solves >=2 tasks = §23.4 codebook seed): table in place, 0 so far
(populate as reused routes generalize). Node/path split now real; next rung = chunk storage (§23.4).

## MASS GROUNDING (§24, 2026-07-01): nucleus dust + copper wires, from Vesica Physics
Read Vesica AI/Physics: mass_as_snake_trail.py (MASS = trail; more mass = slower = the §22 law, derived
earlier), dust_correction.py (0.14 ψ-dust coefficient), ATOM_GROUNDING_RESULTS.md (knot=inert nucleus/stays,
valence/tail=reactive/conductive). Grounded scan_map.ts §24:
- node mass increment = mean nucleus (knot) mass of the solving ops (not arbitrary +3) = snake-trail dust.
- COPPER WIRES: op-transition edges accrete conductance += 0.14*(val_a+val_b)/2; resistance=1/(1+cond),
  falls with reuse. First wires: rotate>tile, swap>fillHoles (cond 0.420), swap>combinePanels (0.280).
- two masses = nucleus (knot, stays, foundation) vs electron-current (valence edges, flows) = a copper wire.
Foundations now in nucleus units; a406ac07 & 903d1b4a & 195ba7dc STOPPED (black holes).
Bounds: knot/valence + 0.14 are grounded; dynamics scalers (STOP_EPS etc) still illustrative; wire reuse
curve populates as op-paths recur. Shared wires = conductive corridors = §23.4 codebook seeds.

## DEPOSITION (§25, 2026-07-01): affinity-sorted layering — metal lines vs organic webbing
Built deposition.ts (from atom_cards: reactivity=|valence|, weight=|knot|, affinity=shared valence),
grounded in knot_tail_reactivity.py + isotopes_chnops_branching.py.
- REACTIVITY LADDER: inert metal lines = identity/flipH/crop/downscale (v0,w5, rigid structure);
  reactive organic = keepLargest/recolor/tile/half (high v, low w = webbing fill). Clean partition.
- DEPOSITION: what layers on each wire by affinity — rotate<-transpose/gravity, swap<-recolor/keepColor.
- LAYERED NUCLEATION: rotate->L1[transpose,recolor,keepColor]->L2[...] (copper attracts more).
- ORGANIC WEBBING: strong light-reactive pairs not yet wires = candidates between the lines.
- GRADIENT: max affinity 5 (near=templated) -> mean 1.90 -> 1034/2278 pairs aff<=1 (far=random dust/void).
Answers all of Jonathan's deposition questions. Bound: affinity=shared-valence is first-order; deposition/
webbing are candidate structures NOT yet wired into search — next step is biasing solvers with high-affinity
deposits on the current best wire (chemistry -> search heuristic).

## SPECIES / ELECTROCHEMISTRY (§26, 2026-07-01): planet-composition test = honest null on tiny n
Built species.ts. From live genomes (species) + atom_cards:
- COMPOSITION: organic 62% of solution op-usage vs 71% DSL baseline = 0.87x (NOT enriched). Solutions
  ~mirror the DSL crust; the CHNOPS-enrichment claim is UNCONFIRMED on n=4 distinct genomes.
- SPECIES-by-branch: 4 lineages from 4 start ops (rotate,swap,cross,fillHoles) — different branches ->
  different species holds. fillHoles = most-used element (carbon-like hub).
- ELECTRON-ONLY vs NUCLEUS-MOVE transitions: 5 vs 4 (electron-only reuses a wire=cheap conduct; grows
  as wires accumulate = decoupling from nucleus = 'free'/conductive). Ties to floor/roof.
Design (captured, not built): displacement-with-provenance, gradient relocation, endpoint-voltage ETC.
Bound: n=4 = first reading not conclusion. Next payoff build: affinity/conductivity biasing the search.

## CHANNELING CYCLE (§27, 2026-07-01): dark-matter router — built, demonstrated, not yet solving
Built channel.ts. Grounded in dark_matter_iceberg.py (dark matter=partials/iceberg), dark_light_transport.py
(move containers to attractor), erdos-incidence-geometry (channels=lines, webs=points, maximize crossings).
- DARK MATTER = 1243 unexplored affine op-pairs (partials). WEBS = laid wires.
- CHANNEL: each web attracts most-reactive dark matter (tile<=keepLargest) -> new wire.
- CYCLE: rotate>keepLargest>keepSmallest>half>... product feeds next web (autocatalytic combine+explore).
- ERDOS: webs sharing a reactive property = a line; 4 productive lines (sym/color/obj/pos).
CAVEATS: (a) greedy cycle collapses into the valence-5 clique (needs diversity pressure). (b) BIG: proposes
candidate compounds, NOT verified solves — §21-27 is a complete grounded memory that hasn't changed a solve.
CRUX/next: feed channeler proposals into the solver as a search bias (channel affine deposit onto a near-miss
anchor, run biased attempt, record if it closes) — the one build that converts the whole edifice to net-new.

## CONSERVATION / BUDGET (§28, 2026-07-01): finite dust, bonding locks, veins deplete
Built budget.ts. Fixes §24/§27 unphysical unbounded accretion + clique collapse.
- INVENTORY from searches: 15 element types, 19 units (fillHoles:3 hub, most 1 = scarce). Finite.
- BUDGETED CYCLE: consumes stock, mines another search's dark matter when depleted (3 mines), halts at
  "all dust consumed -> run a NEW search". Conservation = the diversity pressure that fixes §27 clique.
- BONDING LOCKS (Fe+O=rust): free 19 -> free-left 0, bonded 36; recover only by decomposition at a cost.
- VEINS DEPLETE: foundation pumps product while problems open; solved -> production stops, dust frees.
Budget is now the trigger: finite dust = finite moves; "new search" = when to spend compute.
Unrun crux remains: let the budgeted channel drive a biased solve, record if it closes net-new.

## CLOSED-CYCLE MAP EXPANDER (§29, 2026-07-01): reachability, not solving — the reframe
Built cycles.ts. Jonathan's reframe: §21-28 is a MAP-EXPANDER (find where solves could be), not a solver.
Mechanism: commit a reaction only if a RETURN PATH (closed cycle) exists — forces over-exploration, widens
map, guarantees returnable/safe territory.
- COVERAGE: 15 seed ops -> 55/68 (81%) reachable. Closed-cycle coverage == one-way coverage (55) => graph
  strongly connected => requiring reversibility costs NO coverage here (safe exploration is free).
- 51 ops touched hunting return paths (forced over-exploration). 4001 viable closed cycles.
- EVOLUTION/BUDGET: cycles compete for finite dust; EV=reactivity/cost ranks the gamble under budget.
- FRAMING (Jonathan): answers aren't on these void lines; this gives better STARTING POSITIONS. Hand the
  55-op returnable domain to the real solvers (§18 closers) instead of 15 raw seeds.
Resolves the "hasn't solved anything" tension: wrong metric — the job is coverage, and coverage succeeded.

## PAYOFF TEST (§30, 2026-07-01): middle-shell-biased solver vs uniform — weak positive on coverage
Built dna_biased_scan.ts (same GA, mode base=uniform vs bias=follow affinity edges = §29 reaction network).
3 matched runs each, eval 0-90:
- base: 2,1,1 -> mean 1.33/run, 3 distinct tasks (21f83797,34b99a2b,358ba94e)
- bias: 2,3,0 -> mean 1.67/run, 5 distinct tasks (adds 31d5ba1a,0c786b71)
READING: bias reaches MORE distinct tasks (5 vs 3), incl. ones base never found = wider reach/coverage
(consistent with the map-expander "better starting positions" reframe). Per-run count higher (1.67 vs 1.33)
but WITHIN NOISE (variance high, n=3). Honest: weak positive on COVERAGE, inconclusive on solve rate.
First time §21-29 touched the real solver; moved its footprint in the predicted direction.
NEXT: many matched runs over full 400, measure UNION coverage (bias reaches tasks base can't) not per-run.

## FOLD / BALANCE ACCEPTANCE (§32, 2026-07-01): outer-shell balance criterion — works but strict
Built fold_scan.ts. K=3 strands/task; accept only if >=2 agree (unanimity) AND span>=4 property-dims
(torque-free, §31). vs LONE (any single strand). Eval 0-200:
- LONE: 11 accepted, 10 correct = 91% precision (miss = 5ffb2104, an overfit).
- BALANCED: 1 accepted, 1 correct = 100% precision, abstains on 10.
READING: balance REJECTED the lone overfit (5ffb2104 had no counterweight -> abstain) and accepted only a
correct balanced assembly (60c09cac) = §31 criterion validated directionally. But coverage collapsed to 9%
(abstains on 9 correct-but-lone solves). Grounded in §31.2 (most per-task solves ARE lone points). n tiny.
FIX/join: combine with §30 middle-shell bias so strands AGREE when right (raise balanced coverage, keep
precision). Full outer-shell solver = §30 bias (agree when right) + §32 balance (reject lone points).

## EXPAND-CONTRACT (§33, 2026-07-01): per-atom coordinate descent from bounce anchor — +0 (4th wall confirm)
Built contract_scan.ts: from bounce near-miss anchor, coordinate descent (replace/insert/delete ONE op at
a time, affine-biased) until exact train fit. Full 400: bounce base=13, contraction ADDED 0 (net-new 0).
READING: 4th independent fixed-move attack on ~0.99 near-misses to give +0 (after §16b deepen, §17 bond,
§18.7 lateral). Strongly re-confirms §18.8: the residual is a LEARNED PARAMETER, not a missing arrangement
of fixed atoms — no per-atom pull-back lands on it. closer2's learned map (§18.19,+1) remains the only closer.
HONEST GAP: contracted from a single anchor, not the maximally-expanded §29 domain (Jonathan's "expand the
whole surface first"). Coupling §29 expansion -> §33 contraction is the untested truer variant.

## KERNEL TIER (2026-09-29): Lean-Kernel-Challenge gates as a trust filter. Precision rises to ~95% on held-out eval
Built src/kerneltier.ts. It uses the gates from the SAIR/Lean FRO Lean Kernel Challenge: a submission counts
only if it is total, proven for EVERY input (passing tests is not enough), and not a lookup table.
- The program is picked WITHOUT test peeking: the first stage that fits train.
- K1: total. K2: leave-one-out re-induction reproduces each held-out train pair. K3: the LOO programs give
  the same test answer as the full program.
Results:
- training: 107 train-fit programs, test precision 86.9%. Kernel-accepted 75 -> 96.0% (72/75). Blocks 11 of
  14 wrong answers; loses 21 correct.
- EVAL (held out): 34 train-fit programs, 79.4%. Kernel-accepted 21 -> 95.2% (20/21). Blocks 6 of 7 wrong
  answers; loses 7 correct.
READING: this is the §32 direction (precision up, coverage down), but the kernel gate keeps far more coverage
than balance (21 vs 1 accepted). Most correct-but-rejected tasks have 2-3 train pairs, too few to re-induce
after dropping one. Use it as the COMMIT gate for the trusted rule library and as the confidence signal when
attempts are limited. Outputs: kernel_tier_data.json, kernel_tier_data-eval.json, out_kernel_*.log.
