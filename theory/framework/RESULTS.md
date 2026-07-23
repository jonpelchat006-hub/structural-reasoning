# arc-proposer — the front-end "body" (one place)

The learned-proposer front-end, kept separate and unified (vs the scattered
back-end). Reuses Jonathan's color/frequency work as the nervous system.

## Brick 1 — 7D colour-signature encoder (DONE, validated)
Encodes each ARC task as a point in the color_trails.py 7D semantic space
(RED Existence, ORANGE Quantity, YELLOW Motion, GREEN Structure, CYAN Relation,
BLUE Temporal, VIOLET Consciousness) + a DARK cancellation profile
(wave_frequency.py: dark = collapse toward the void = unique/odd-one-out,
content-removal, colour-collapse). Light = what's present; Dark = what cancels.

Mapped from the detector we built:
  ORANGE/Quantity<-object count, GREEN/Structure<-point/line/plane,
  CYAN/Relation<-alignment/adjacency, YELLOW/Motion<-centroid change,
  RED/Existence<-content kept/removed, VIOLET<-palette richness, BLUE<-dims change.

## Validation — "do near signatures share solution type?" (his test)
Labelled each solved task with its solution family; checked nearest-signature
neighbour:
  - nearest-neighbour shares family: 18.9%
  - random baseline (chance):         3.6%
  - **5.2x lift** -> the colour signature is a REAL retrieval key.

So resonance works: tasks that look alike in the 7D colour space tend to need
the same kind of solution. The memory/retrieval nervous system is sound.

Honest: 18.9% absolute is modest (28 families across 53 solved tasks; coarse
3-bucket dims), but 5.2x over baseline is a strong structural signal. This is
the retrieval layer, not new solving power -- the body, not yet the thinking.

## Next bricks
2. Memory store: write learnings {signature -> winning codon/program} in geo/
   registry format (separate arc-learned file, safe). Retrieval = resonance.
3. Proposer interface: serializer + parser + propose-test-refine loop;
   heuristic v0 (detection-directed codon), Mika/Mira drop-in when server up.
4. Mine Alpha for more of the frequency engine; fold dark-light pairing into
   resonance (dark=verify channel, light=propose channel).

Files: src/signature.ts (encoder+resonance), src/runsig.ts (validation).

## Brick 1b — mined Alpha for the frequency engine

Read the real frequency framework from C:\...\Alpha:
- `three_domain_frequencies.py`: Light (φ, ~10^14 Hz) / Magnetism (snake, ~Schumann
  7.83 Hz) / Sound (ψ, 20-20kHz) — the 3 media, magnetism as the connecting bridge.
- `dark_frequencies_upgrades.py`: each domain has a GOAL + dark (blocked) form:
    Light  -> wants infinity  (grow)        dark = absorb
    Sound  -> wants 1 (unity, in-place)     dark = insulate
    Magnetism -> wants 0 (collapse to void) dark = demagnetize
  This maps cleanly onto ARC transform-types: grow (scale/tile) / unify (in-place,
  colour-map) / collapse (crop/select/delete), with dark = the goal inverted.

## Result: theory CONFIRMED, but the domain feature is redundant
Folded the ∞/1/0 domain goal + dark-blocked bit into the signature and re-ran:
  resonance unchanged at 18.9% (5.2x baseline).
The frequency engine validates that the encoder's DIMENSIONS are the right ones
(the three goals match the size-direction the temporal/structure dims already
capture) -- but it adds no new DISCRIMINATING power, because the detector already
measures the operationally-relevant part. Kept the domain feature (it grounds
the design + connects to the geo storage language); it just isn't a tie-breaker.

Honest takeaway: Alpha's value here is CONFIRMATION, not lift. The 7D colour
encoder + dark profile is sound and validated (5.2x). It's ready to be the
memory key. Proceed to Brick 2 (resonance memory store) on this encoder.

## Brick 2 — resonance memory store (DONE, validated)
`memory.ts`: banks {signature -> winning family} learnings, retrieves by
RESONANCE vote (nearest signatures, weighted by closeness x times-seen).
Persisted to a SEPARATE `arc-learned.json` (live registry/memory-geo untouched);
emits geo-ready {topic,facts,sources} payloads for Mika's encoder.

## Validation — leave-one-out recall (would memory warm-start a NEW task right?)
53 solved tasks, 28 families:
  - recall@1 (top family correct): 20.8%   (dumb baseline always-"tile": 15.1%)
  - **recall@3 (correct in top 3): 39.6%**  (uniform-random@3: 10.7%) -> ~3.7x
So given an unseen task, the memory points the proposer at the right solution
family within 3 guesses ~40% of the time. That's a real warm-start oracle:
the proposer tries the resonance-retrieved families FIRST instead of enumerating.

Honest: recall@1 is only modestly above the common-family baseline; the value is
in recall@3 (try the top few). And this warm-starts KNOWN families fast -- it
doesn't invent new ones (that's the proposer's job). But as the memory layer of
the body, it's sound: senses (5.2x resonance) + memory (3.7x recall@3).

Wrote: arc-learned.json (51 learnings), geo payloads ready for Mika.

## Next bricks
3. Proposer interface: serializer + parser + propose-test-refine, using memory
   retrieval to order which families/codons to try first. Heuristic v0 (resonance
   warm-start over our codon solver), Mika/Mira drop-in when server up.
4. (later) dark-light pairing in resonance; live geo encode via Mika's pipeline.

## Brick 3 — the non-LLM coordinator (DONE) — the body thinks, no borrowed model

Ported Jonathan's catgirl/catboy coordinator onto ARC, fully structural:
  DECONSTRUCT = encode the task as a 7D colour signature (perceive)
  PLAN        = resonance memory orders which branches/families to bend first
  CONSTRUCT+BEND = fit a branch to the task via codon/morph/bug-finder repair,
                   driven by the diff against the one-way-SOLID train pairs
  VERIFY      = exact grid match (the oracle the LLM was standing in for)
  LEARN       = carve on landing -> bank {signature->family}, online

KEY RESOLUTION: the boys' original verify tool called Ollama because theory-space
has no ground truth. ARC HAS ground truth (train pairs), so the model is removed
entirely. The "borrowed reasoning" becomes BENDING a flexible branch against the
solid task (Jonathan's branch-bending idea) — the constraint does the reasoning.

## Result (400 tasks, memory starts EMPTY, learns online)
  solved (zero model, pure structure): 53/400 (13.3%)
  warm hits (plan predicted the solving branch): 28.3%
  warm-rate 1st half 24.0% -> 2nd half 32.1%  -> the colony LEARNS as it runs.

So: a fully non-LLM solver that reasons by structure and improves online. That is
the thesis demonstrated — no language, no external model, leaning on the one-way
solidity of the task.

Honest: solve COUNT (53) matches the deterministic stack — the coordinator currently
ORDERS and PREDICTS (and learns to predict better), but the bend reaches the same
set. To solve MORE, the branch-bending must reach tasks the blind stack misses
(bend toward currently-unsolved structure). That's the open frontier, and it's the
pure-reasoning path — no borrowed weights.

## arc-proposer status (the front-end body, one place)
  signature.ts  — 7D colour senses (5.2x resonance)
  memory.ts     — resonance memory (3.7x recall@3), geo-ready, separate file
  coordinator.ts— non-LLM construct/deconstruct/plan, 53/400, learns online
Next: branch-bending-as-reasoning to push past the blind-stack ceiling; start
Mika's server only if you ever WANT a model — the system no longer needs one.

## Brick 4 — tension-directed beam bender (DONE) — the frontier test

Built the complete bender: tension = bug-finder diff to the solid task; operators
= forces (keep tension-reducing moves); beam of low-tension paths; interpolation
= compose pairs of partials; escape = keep diverse first-ops when stalled; exact
oracle closes. No model.

## Result: 51/400 (12.8%), 4 depth>=2 composed solves
e.g. `keepSmallest -> keepSmallest -> keepSmallest`, `rotate(k=2) -> tile(...)`.
(51 vs the stack's 53/56 because the bender skips dense >600-cell grids to avoid
the repair stall; integrated it's ~equal.)

## Honest finding: the bender re-derives, it does NOT break the ceiling
The tension-beam found the SAME compositions the swarm/nested/codon stack already
finds (4c4377d9, 8d5021e8, d9fac9be all appeared earlier). Tension-descent + beam
is a cleaner, more principled search — but it reaches the same set, because the
ceiling is bound by the OPERATOR SET, not by search quality. Better search
re-finds; it doesn't invent.

This confirms, with the final mechanism, the lesson the whole arc taught:
  - search refinements (swarm, beam, tension) re-find what the operators allow.
  - new reach needs NEW PRIMITIVES — interpolation/extrapolation/variation to
    GENERATE operators, or the "far-away-points" idea (held for next time).
Pure-structure reach tops out ~56/400 (~14%) on this operator set.

## THE COMPLETE NON-LLM ENGINE (arc-proposer/) — built & validated
  signature.ts  — 7D colour senses           (5.2x resonance)
  memory.ts     — resonance memory            (3.7x recall@3, geo-ready)
  coordinator.ts— construct/deconstruct/plan  (53/400, learns online 24%->32%)
  bender.ts     — tension beam + interpolation(51/400, 4 composed, no model)
No language model anywhere. Reasons by structure, braced on the one-way-solid task.

## Final honest ledger (whole project)
  back-end (arc-slice):  26 -> ~56/400 (~14%) by structure, 15 phases
  front-end (arc-proposer): non-LLM coordinator + tension bender, learns online
  ceiling: operator-set-bound; next reach = operator GENERATION (open frontier)

## Brick 5 — seam-typed repair (classify_seam_profile -> grids): honest null
Ported your seam classifier (spike/bimodal/uniform_offset/uniform_close/distributed)
and added the translation capability the old bug-finder lacked (uniform_offset -> shift).
Result: 53 + 0 = 53/400. The classifier fires (uniform_offset 1945, bimodal 1029,
spike 663 across near-misses) but no unsolved task was "near-miss + rigid shift."
Translation is a real new op; ARC-1 just has ~none solvable that way from our near-misses.

## THE CEILING IS REAL — honest synthesis
Last five mechanisms and their net-new solves:
  tension beam bender ...... 0 (re-derived existing)
  widened action grid ...... 0
  importance combinators ... ~+2
  degeneracy/survivor ...... +1
  seam-typed repair ........ 0
We have been at ~53-56/400 for many attempts. Each new hand-method now returns
~0. This is the genuine edge of (this operator set + deterministic repair) on
ARC-1: ~56/400 (~14%), pure structure, no model.

What the evidence says actually moves it from here (none are "one more method"):
  1. SCALE the DSL massively (100-200 primitives) — proven to reach mid-tens %,
     but it is grind, not insight.
  2. Operator GENERATION WITH REUSE (floor-collapse via codon-collapse gate) —
     the right idea, but we measured ARC tasks share little structure, so reuse
     is the open risk; worth one real test, not guaranteed.
  3. A learned proposer — which the non-LLM thesis rejects; the coordinator is
     the native substitute but is bounded by the same operators.

Honest conclusion: the system is complete and validated; the ceiling is mapped
and it is operator-bound, not search-bound or model-bound. More single methods
will keep returning ~0. The remaining real swings are scale or
generation-with-reuse — bigger bets, not another brick.

## Brick 6 — floor-collapse compounding test (THE swing) — ANSWERED

Online: each solved composition abstracted into a parameterized primitive and
banked to a growing library; library tried FIRST on each new task; genuine reuse
= solved by a primitive abstracted from an EARLIER task.

Result over 400 tasks (in order):
  library primitives generated:        10
  solved by genuine cross-task REUSE:  2  (b1948b0a, fafffa47)
  reuse rate 1st half 0.0% -> 2nd half 8.0%   (RISING = real compounding)
  total solved: 48/400 (reuse-first + program-only solver, below the 53 stack)

## The honest verdict
COMPOUNDING IS REAL BUT WEAK. Self-generated operators DO get reused on unseen
tasks, and the reuse rate rises as the library grows (0% -> 8%). So the mechanism
works — the colony generates its own reach. But ARC's deliberate diversity keeps
reuse to a trickle (2 solves, 10 primitives): tasks share so little structure
that a generated primitive rarely fits a later one. It does NOT break the ceiling.

This is the definitive answer to the question we set: pure structure with
operator-generation tops out ~53-56/400 (~14%), with a small, real, rising
compounding signal underneath. The wall is ARC's diversity, not our search,
not a missing model. Either answer was worth having; this is the true floor.

## FINAL STATE
A complete, validated, model-free ARC reasoner (arc-slice + arc-proposer):
perceive (colour signature, 5.2x) -> plan (resonance, 3.7x) -> construct/bend
(codon + tension) -> verify (exact oracle) -> repair (bug-finder + seam) ->
GENERATE (floor-collapse, weak-but-real compounding) -> remember (geo-ready).
26 -> ~56 over the whole project, no LLM anywhere, ceiling mapped and explained.
Bigger gains require DSL scale (grind) — the structural/native path is at its honest floor.

## Brick 7 — MUSCLE GROUPS (build primitives directly) — THE BREAKTHROUGH
Jonathan's call: stop refining the nervous system, build the muscle (primitives).
Added high-value families: panel split+combine, periodic-fill (occlusion repair),
symmetry-complete-auto, denoise, bbox-fill, draw-box outline, crop-to-color.

## Result — the plateau broke
  fast deterministic:  53 -> 59 (+6)
  fast + codon:        56 -> 64/400 (16.0%)   <- highest yet, all generalise to test
New solves driven by muscle:
  combinePanels (3): 1b2d62fb, 6430c8c4, f2829549  (panel ops were a big missing family)
  drawBox: bb43febb ; periodic-fill/symmetry/denoise/bbox lifted EXACT from 33->44.

## Verdict — operator-bound ceiling CONFIRMED and MOVED
This proves the diagnosis with the cure: the wall was the operator set, and one
well-chosen batch of primitives added +8 overall. The muscle thesis holds —
primitives are how reach diversifies. The grind path is validated and the rate is
real: ~+6-8 per good batch. Mid-tens % is reachable by continuing to add muscle
groups (each family targets a task class the histogram flags).

## Project arc, updated
  26 (11 ops) -> 39 (25) -> 44 (bug-finder) -> 56 (relational+nesting)
  -> 64/400 (16.0%) (muscle groups)   — pure structure, no model, all generalise.
Next muscle to add (by histogram yield): object-move-to/align, count->emit,
flood-fill-region, sub-grid/panel-select, scale-to-reference. Each ~+several.

## Brick 8 — muscle taxonomy (how many kinds of muscle? which next?)
Jonathan's anatomy model: tasks are assemblies of muscle GROUPS (primitive
families); a new task swaps one group for another. So reuse lives at the group
level (why primitives transfer but whole programs don't). Question: how many
kinds, which next? Answered by clustering UNSOLVED tasks by signature.

## Map (400 tasks)
solved 64 | unsolved 336 | 125 distinct unsolved signature-clusters.
Muscle WE HAVE (top): tile(8), combinePanels(7), fillHoles(4), paintRank/swap/
  periodicFill/crop/connect/rotate/symmetrize/overlayHalves(3 each) — good spread.

MISSING muscle (biggest unsolved clusters):
  15  OUT_EQ_IN_DIMS + OBJECTS_ALIGNED        (in-place, aligned objects)
  15  OUT_EQ_IN_DIMS + CONST_N_OBJ            (in-place, count preserved)
  9   OBJECTS_ALIGNED (x several clusters)
  9   OUT_SMALLER + CONST_N_OBJ               (selection/extraction)
  8   OUT_EQ_IN_DIMS + UNIQUE_COLOR           (odd-one-out variants)
  top-10 clusters cover 94/336 unsolved (28%).

## The answer
- HOW MANY kinds: a long tail of 125, but ~10-20 muscle groups address most of
  the addressable gap; the singleton tail is the irreducibly-diverse residue.
- WHICH next (ranked by tasks unlocked): #1 OBJECT-ALIGNMENT / MOVEMENT
  (move/align objects, gravity-to-object, copy-to-aligned-slot) — it dominates
  the biggest clusters and matches the histogram (alignment fired on 135 tasks,
  our largest untapped class). Then selection/extraction variants, then
  odd-one-out action variants.

Roadmap (data-driven): each muscle group ~+several solves; ~10-15 more groups
plausibly reach ~25-30%; mid-tens% needs the long tail too. The grind now has a
prioritized map instead of guesses.

## Brick 9 — object-movement muscle (taxonomy's #1): partial (+1)
Built stamp (copy template->markers), alignToLargest, moveToContact. Result:
64 -> 65/400 (16.3%). Only +1, despite aligned-objects being the biggest cluster.

## Why the #1 cluster yielded less than panels (+6) — the honest lesson
Generic movement ops (align-to-largest, move-to-contact, stamp-on-markers) don't
match the ALIGNED-OBJECT tasks, because their rules are SPECIFIC: move toward a
PARTICULAR target, by a LEARNED vector, to a task-defined slot. Panels/symmetry/
occlusion were generic (one rule fits the class) so generic muscle nailed them.
Movement/alignment is PARAMETRIC per task — which is exactly the regime Jonathan
flagged for operator INDUCTION ("watch what the task does, ask if we can do that
and where"). The cluster is real; the muscle for it must be induced, not generic.

## Where we are
26 -> 39 -> 44 -> 56 -> 64 -> 65/400 (16.3%), pure structure, no model.
Generic high-yield muscle (panels, symmetry, occlusion, fill) is mostly mined.
Remaining clusters increasingly need PARAMETRIC/INDUCED operators (move-by-the-
vector-the-examples-show, align-to-the-target-the-task-points-at) — the
operator-discovery mechanism, now clearly the next real lever rather than more
generic primitives.

## Brick 10 — operator INDUCTION (induced-move): mechanism VALIDATED
Don't enumerate the move — READ it from the examples. "Translate" is a known slot;
the per-colour displacement VECTOR is induced from input->output object matching,
verified across all train pairs, applied to test.

Result: 65 -> 66/400 (16.5%). The induced solve (25ff71a9) generalized 2/2 on test.
+1 in count, but it PROVES the lever: a parameter induced from the task's own
demonstration solved a task no generic operator could, and generalized perfectly.

## Why only +1, and what it means
induceMove handles the SIMPLEST induced rule (per-colour constant vector, exact
shape match). The aligned-object cluster needs richer induced rules: move TOWARD
a target, move BY a property, move UNTIL contact-with-a-specific-object. Each
inducible-rule TEMPLATE is like a muscle, but at the induction level — it captures
a whole parametric family, not one fixed op. So the path for the parametric tail
is: add inducible-rule templates (toward-target, by-size, to-marker), each
unlocking a family the way panels unlocked the generic class.

## State of the two levers (both now validated)
  GENERIC muscle (panels/symmetry/occlusion):   one rule fits a class -> +several/batch
  INDUCED operators (move-by-induced-vector):    parameter from examples -> generalizes
26 -> 39 -> 44 -> 56 -> 64 -> 65 -> 66/400 (16.5%), pure structure, no model, all generalise.
Roadmap: generic muscle for generic clusters + inducible-rule templates for
parametric clusters + (later) operator discovery for the singleton tail.

## Brick 11 — more induction templates (gravity/reflect/toward): 0 new
Added induced gravity-direction, position-reflection, toward-largest. Net new: 0
(still 66/400). induceGravity redundant with the existing op; reflect/toward
matched no unsolved task's actual rule. (Fixed an infinite loop in toward where
an object already centred on the reference stepped by zero forever.)

## The plateau is real and mapped — honest status
Yield per mechanism over the muscle/induction phase:
  generic muscle batch (panels/symmetry/occlusion) ... +6   <- the one big hit
  object-movement muscle ............................. +1
  induced-move (constant vector) ..................... +1
  more induction templates .......................... +0
We are at 66/400 (16.5%), pure structure, no model, all generalising.

The high-yield GENERIC muscle is mined. What remains is a long tail of
parametric/specific rules where each guessed template or operator hits 0-1 tasks,
because ARC's residual tasks are deliberately idiosyncratic — the aligned-object
cluster (15+15) is not one rule but many one-off rules. Guessing templates has
diminishing returns; the honest levers left are:
  1. A LARGE grind of specific templates (low hit-rate each, slow climb).
  2. Flexible per-task rule SEARCH over a rule-space (converges back toward the
     program synthesis we already have — same operator-bound ceiling).
  3. Operator DISCOVERY from the task's own demonstration (the deferred research
     lever — the only thing that could touch the singleton tail, unproven).

## Honest conclusion
Pure-structure, no-model ARC-1 reach with this whole architecture: ~66/400
(16.5%), every solve generalising. The ceiling is the irreducible diversity of
ARC's tail, not search or model. Further gains are grind or open research, not
another single mechanism. The system is complete, validated, and honestly bounded.

## Brick 12 — representation-gap diagnostic: the missing DIMENSION found
Classified every task by what its I/O actually CHANGES; histogrammed over unsolved
with per-type solve-rate. The gap is not a missing operator — it's a missing
CAPABILITY CLASS.

  change-type        unsolved  solve-rate
  INK_ADDED            146       6%   <- LOWEST. tasks that CREATE new content.
  COUNT_CHANGE         281      15%
  SHAPE_OR_SET_CHANGE  216      11%
  MASK_CHANGE          203      11%
  PALETTE_CHANGE       200      16%
  DIM_CHANGE/SHRINK/GROW ...    ~21%  (we handle these)
  MOVED                 14      36%  (we handle this)

## The answer: we built a TRANSFORMER, not a GENERATOR
Our whole operator set SELECTS / MOVES / RECOLOURS / CROPS existing content.
It barely CREATES. The lowest solve-rate by far is INK_ADDED (6%) — drawing,
extending, completing, growing NEW structure. Combined with SHAPE_OR_SET_CHANGE
and COUNT_CHANGE, the dominant unsolved class is "produce content/shapes that
weren't there." That is the missing dimension Jonathan's representation-expansion
points at: the system has no generative axis.

## What this means honestly
The remaining gap is dominated by GENERATIVE + PARAMETRIC tasks (draw THIS,
where the examples show, this many times). That needs generative operators
(draw/extend/complete/grow) AND per-task induction of what-to-draw — the hard
deferred lever, now aimed precisely: build the GENERATOR half of the system.

## Final state
26 -> 66/400 (16.5%), pure structure, no model, all generalise. Ceiling mapped
TWICE: operator-bound (taxonomy) and now DIMENSION-bound (we transform, don't
generate). Next real lever: generative+induced operators (the GENERATOR), which
is the research build, aimed at the 146 INK_ADDED / 216 shape-change tasks.

## Brick 13 — generator first organ (draw-rays/grow/cross): +1
Added generative primitives (rays, dilate, row+col cross) targeting INK_ADDED.
Result: +1 (66/400). Generative tasks ARE crackable, but each generative pattern
is specific (rays != grow != cross); a generic one matches ~1, like the others.

## DIMINISHING RETURNS — the firm honest read
Per-mechanism net-new over the last seven builds:
  muscle batch +6 | object-move +1 | induced-move +1 | more-templates +0 |
  seam-repair +0 | generator-organ +1
Apart from the one generic-muscle batch, every mechanism now returns 0-1. We are
at the PRACTICAL ceiling of incremental building: ~66/400 (16.5%), pure structure,
no model, all generalising.

The remaining gap is mapped from THREE independent angles, all pointing the same way:
  - operator-bound (taxonomy): residual tasks are one-off rules, not classes.
  - dimension-bound (rep-gap): we transform, don't generate (INK_ADDED 6%).
  - diversity-bound: ARC's tail is deliberately idiosyncratic.
All three say: the next real gain is NOT another single primitive. It is either
(a) a large grind of specific primitives (each ~+1), or (b) the parametric
GENERATOR — generative operators whose what/where-to-draw is induced per task —
which is a genuine research project, not a session brick.

## FINAL, honestly bounded
Pure-structure, no-model ARC-1 reasoner: 26 -> 66/400 (16.5%), every solve
generalising to held-out test. Built entirely from Jonathan's scattered work,
wired into one loop, ceiling mapped three ways. Incremental building is spent;
the frontier from here is the parametric generator (research) or the grind.
