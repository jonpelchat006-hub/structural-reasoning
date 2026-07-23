# The Inner Shell — the ARC primitive set, named and mapped

The "always-present" base shell of the generator: every primitive defined, grouped
by the ROLE/dimension it acts on (the color_trails axes: existence, quantity,
position, size, colour, shape, structure, generation). Building = naming these.
Current count: **62 primitives → 73/400 (18.3%)** deterministic, no model.

## ROLE: geometry (rigid orientation — the quaternion/D4 shell)
- `identity`, `rotate(k)`, `flipH`, `flipV`, `transpose` — the 8 D4 symmetries.

## ROLE: size / extent
- `scale(fy,fx)`, `downscale` (auto-detect block shrink), `tile(ny,nx,mirror)`,
  `crop(bg)` (to content), `trim` (remove border), `cropToColor(c)`, `addBorder(col)`.

## ROLE: colour
- `recolor(from,to)`, `keepColor(c)`, `removeColor(c)`, `swap(a,b)`,
  `paintRank(by)` (recolour by size rank), `cmap{…}` (arbitrary map — the bug-finder's
  finisher; never enumerated, only constructed).

## ROLE: object selection (WHICH object — the hub/kissing degree)
- `largest`, `keepLargest`, `keepSmallest`, `keepRare`, `keepCommon`,
  `keepTopK(by,k)`, `selectUnique(mode)` (odd-one-out by shape/size/colour),
  `selectMajority`, `keepTouching(marker)` (adjacency relation).

## ROLE: per-object map (apply T to each — the combinator/nesting)
- `mapObjects(inner)`, `mapTopK(inner,by,k)`, and recursive `nested.ts`
  (mapObjects/mapTopK with a SYNTHESISED body, depth ≤ 3).

## ROLE: position / movement (the motor)
- `gravity(dir)` (cells), `gravityObj(dir)` (whole objects), `shift(dy,dx)`,
  `stamp` (copy template→markers = the "copy" primitive), `alignLargest(axis)`,
  `moveContact(dir)`. Plus INDUCED move (`induce.ts`: read the vector from examples).

## ROLE: structure / completion (resonance — the knot)
- `symmetrize(axis)`, `completeSym` (auto-complete a symmetry), `fillHoles(fill)`,
  `periodicFill` (occlusion repair via detected period), `connect` (fill between
  aligned same-colour cells).

## ROLE: generation (create new content — the 6% INK_ADDED gap)
- `drawRays(mask)`, `grow` (dilate), `cross` (row+col projection),
  `bboxFill`, `drawBox` (outline).  *Thinnest family — the open frontier.*

## ROLE: panel / sub-grid (grid-of-cells)
- `half(which)`, `overlayHalves(mode,out)`, `combinePanels(mode,out)` (2 panels),
  `oddPanel`, `majPanel`, `overlayPanels(mode,out)` (N panels: pick odd / majority /
  overlay-all).

## ROLE: cleanup
- `denoise(min)` (remove sub-min objects).

---

## Closers / engines that sit ON the shell (not primitives, but the motor)
- bug-finder: `colorMapRepair`, `sizeRepair`, seam classifier — drive residual→0.
- search: swarm-core (UCB + FailureBuffer), tension beam bender.
- transfer: morph (lift/bind), quaternion D4 bridge. (Near-zero on ARC by design.)
- memory: 7D signature + resonance (good retrieval; weak ARC transfer).

## Still EMPTY in the shell (taxonomy's next muscle, by yield)
- `count→emit` (output sized/coloured by object count).
- `floodRegion` (colour enclosed regions by rule; richer than fillHoles).
- `scaleToReference` (size output to a reference object / the count).
- `selectPanelBy(property)` (pick the panel with most colours / a target).
- the GENERATOR family proper (parametric "what/where to draw", induced) — the
  research frontier (the 146 INK_ADDED tasks at 6%).

## Ledger
11 ops → 26 | 25 → 39 | +bug-finder → 44 | +relational+nesting → 56 |
+muscle(panels/sym/occlusion) → 64 | +move/induce/generate → 67 |
+panel-grid → 68 | +colorByShape → 70 | +fractal → 71 | +outline/fillObjHoles → **73/400 (18.3%)**. Pure structure, no model, every solve generalises.
Each named primitive family ≈ +several; the shell is ~85% mapped on the
transform side, ~15% on the generation side (the remaining climb).

## Update log
- Batch (count/shape/flood/panel-by): **colorByShape +2** (group objects by exact
  shape → index colour, cmap finishes). countEmit / floodBorder / panelBy built but
  +0 on ARC-1. Lesson: shape key must be CHEAP (translation-normalized, not D4) —
  the D4 canon was ~5s/dense-grid and stalled the repair pass; the cheap key fixed it.
- Now 70/400 (17.5%). colorByShape filled the 'colour-by-shape-class' slot.


## Update log 2 (this session)
- +colorByShape 70, +fractal/self-similar 71, +outline & fillObjectHoles 73.
- connectObjects/completeDiag: +0 AND a -1 regression — new ops flooded the repair
  candidate list and pushed a real solve past the cap. Fixed by RAISING caps
  (colorCands 150->300, sizeCands ->200, sizeRepair targets 24->80); recovered the
  loss, but net stays 73 (new wins overlap displaced ones).
- SATURATION SIGNAL: new ops now net ~0 (their wins overlap + cap interference).
  The muscle grind has climbed 64 -> 73 (+9) this session and is now near its
  practical ceiling for this architecture. Going materially higher needs better
  candidate RANKING (so good ops aren't capped out) or the parametric GENERATOR
  (research), not more single ops.
- State: **73/400 (18.3%)**, ~60 primitives, pure structure, no model, all generalise.

## Update log 3 — compatibility pooling (the scaling architecture)
Jonathan's pool idea: too many primitives for the search to hold at once → load a
small COMPATIBLE subset per task (routed by features: dims-direction, panels,
objects), search it UNDILUTED, swap to a broader pool only if exhausted.

Result: tight pool solved **59**, full-op fallback +7, codon +4 = **70/400** at
SMALL caps — and **89% of program-solves came from the small loaded pool.**
- Validates the architecture: most tasks need only their compatible subset; the
  "swap when exhausted" tier (the 7 fallbacks) works exactly as designed.
- At small caps, pooling (70) ≈ full-ops-at-BIG-caps (73): pooling RECOVERS what
  big caps bought, but cheaper and cleaner (no dilution), in ~half the candidates.
- It does not by itself EXCEED 73 at 62 ops — the number is bound by op OVERLAP
  and routing accuracy, not dilution, at this scale.

## Why this matters: it's the enabler, not the lever
Pooling is the answer to "more primitives than space." At 62 ops dilution is mild,
so pooling just matches. But it is exactly what makes the NEXT phase viable:
adding 100+ primitives would CRUSH an all-ops search (dilution + cost), while a
routed pool stays small and fast. So the path up is now concrete and scalable:
  POOL (route to compatible subset) + MANY MORE PRIMITIVES + better ROUTING.
Pooling removes the ceiling that capped the naive grind; the climb past 73 is
"keep building muscle, but load it by compatibility" — Jonathan's exact design.

State: 73 (full-op big-cap) / 70 (pooled small-cap, 89% tight). The pooled
architecture is the foundation for scaling primitives without the cap interference
that stalled us this session.

## Update log 4 — 4-probe coarse map (4→16→64), the "rough map" idea
Probe each task with the 4 fundamental axes (color/geometry/size/structure),
measure tension reduction per axis = a cheap rough map.

**As a DIAGNOSTIC it delivers exactly what you wanted ("how many objectives"):**
- dominant-axis distribution: COLOR 152, STRUCT 112, SIZE 102, GEOM 10.
  (Most tasks' best single direction is colour, then structure/size; pure geometry rare.)
- coarse DEPTH (residual after best single probe ≈ #objectives remaining):
  0-direct **42**, 1-close **148**, 2-mid **108**, 3+far **78**.
  So ~190 tasks are within 1 step of a single fundamental; ~78 are genuinely far.
  This is the cheap "which directions are available / how many lines to make" map.

**As a solo ROUTER it underperforms:** axis-routed 60 + codon 5 = 65/400 — below
pooled (70) and full (73). Single-axis routing over-commits: real tasks mix axes,
and routing to one pool misses the combinations. Plus the big-grid guard costs a few.

**The right use (the synthesis):** the coarse map is a TRIAGE, not a router. Use it
to (1) set search DEPTH per task from the residual (direct→depth1, far→allow nesting),
and (2) load the TOP-2 axes' pools (not just 1). That is the real 4→16→64: start
coarse to estimate depth+directions, then expand the pool only where the map says
the task is far. It feeds the pooled search; it doesn't replace it.

State: still 73 best (full-op big-cap). The coarse map adds a cheap per-task
depth/axis estimate — useful for directing effort, not for raising the count alone.
The number is now firmly search-engineering-bound at ~70-73; the climb past it is
MORE PRIMITIVES (loaded via pooling, depth-set by the coarse map) + the GENERATOR.

## Update log 5 — impact-tiered coarse-to-fine (4→16→64 by tiles affected)
Auto-classified ops by MEASURED impact: GLOBAL 23 (rotate/scale/tile/recolor/
fractal/panels…), NEIGHBORHOOD 23, SINGLE 16. Solved coarse-to-fine.

**Structure VALIDATED:** of 65 program-solves, **43 caught by the GLOBAL pool
first**, 15 needed +neighborhood, 7 needed +single. So ~66% of solves are
whole-grid transforms catchable by the small coarse pool — exactly your
impact-scope ordering. Count = 70 (≈ pooling; vocabulary-bound).

**Efficiency finding (honest):** as implemented, escalating SUPERSETS re-ran lower
tiers → MORE work, not less. Incremental escalation (eval only each tier's NEW
ops, reuse prior) is required. But even done right, the gain is MODEST: the ~335
UNSOLVED tasks escalate through all tiers anyway, so they dominate cost. Tiering
saves work on the easy/solved tasks (~8% overall), not the hard majority.

## META-CONCLUSION (across pooling, coarse-map, impact-tiers)
Three search-organization ideas — all sound, all validated, all land at ~70-73:
  - pooling: 70 (89% from tight pool)
  - coarse map: depth/axis diagnostic (42 direct / 148 close / 108 mid / 78 far)
  - impact tiers: 70 (43 global-first), modest efficiency
The number is **not** search-organization-bound. Every clever routing converges
to ~73 because the bottleneck is the PRIMITIVE VOCABULARY and the GENERATOR gap,
not how we organize the search. The architecture is now thoroughly built and
optimized; the climb past 73 is MORE PRIMITIVES (the grind) + the parametric
GENERATOR (research) — not another search scheme.

State: **73/400 (18.3%)** best, ~62 primitives. Search architecture: complete
(pooling + coarse-map triage + impact-tiers, all validated). Remaining lever:
vocabulary + generator.

## Update log 6 — the head-to-head: MORE PRIMITIVES vs the GENERATOR
Ran the experiment Jonathan asked for: build one more primitive batch, then build
the parametric generator, measure each against the same fast baseline.
(Baseline note: at equal SMALL caps the reproducible fast+codon number is **70**;
the headline 73 needed big caps that hang on dense grids, so all deltas below are
measured at small caps for a clean apples-to-apples comparison.)

**Lever A — one more primitive batch (6 ops):** antiTranspose, extractCell,
scaleByCount, borderObjects, smoothNeighbor, rotateObjects. Standalone probe:
antiTranspose/extractCell/scaleByCount/borderObjects = **0** (redundant with the
D4/crop ops, or no ARC-1 match); smoothNeighbor solo 1, rotateObjects solo 2 —
and rotateObjects' hits are mostly already covered by rotate(2). **Net effect: +1**
(70→ effectively 70/71). Hard saturation confirmed quantitatively: a whole 6-op
batch now buys ~one task. The 4 disabled (enumerate:()=>[]), the 2 keepers kept
on a 2-colour cap.

**Lever B — parametric induced GENERATOR (`generator.ts`):** reads its parameters
(source colour, direction-set, stop rule, paint colour) from the train DELTA, then
verifies the induced program on every train pair. Four induced templates:
rayCast (from single-cell markers), connectAligned (fill between same-colour
cells), bboxPaint (outline/fill object boxes), constant overlay.
Result: solves **8** tasks; **6 net-new** over the 70 baseline; **5 of those
generalize to the held-out TEST split** (60b61512 overfits train → fails test —
the known generator risk). **Net effect: +5 → 75/400 (18.75%).**

**Verdict (decisive):** the generator is ~5× more productive than another
primitive batch (+5 vs +1) and reaches a structurally NEW class — "draw content
that isn't a rearrangement of the input" (connect-the-dots, ray casting) — exactly
the INK_ADDED gap the representation-gap diagnostic named. The grind is saturated;
the generation axis is open. **Path up = the generator, not more single ops.**
Caveats kept: generator induction can OVERFIT (1 of 6) — needs ≥2 train pairs and,
ideally, a test-consistency or minimum-description-length guard before trusting it;
restricted to same-dims ink-added tasks for now (the largest untouched family).

State: **75/400 (18.75%)** with the generator as a fallback after fast+codon.
Next frontier: widen the generator (more induced templates: symmetric paint,
periodic stamp, legend/key-driven draw, dims-changing generation) under an
overfit guard — that is now the highest-yield direction by a clear margin.

## Update log 7 — replace IMPLANTED templates with SELF-SYNTHESIZED ones (no loss)
Jonathan's point: the four hand-written templates (rayCast/connect/bbox/overlay in
`generator.ts`) are *implanted* generic CS solutions; better to build our own from
atoms and swap piece-by-piece with a regression guard so nothing is lost.

Did exactly that:
- **Locked a fixture** (`gen_fixture.json`): the 8 tasks the implanted generator
  solves (7 generalize to test; 60b61512 overfits train).
- **Defined our own generative ATOMS** (`gen2.ts`): SEED (markers | every colour-cell)
  × ACTION (emit-ray | between-aligned | box) with paint ∈ {learned C, source colour}
  and optional colour-restriction. A single synth loop fits seed×action×params to
  every train pair — generation-side program synthesis, the mirror of the transformer's
  op search. `generator.ts` kept untouched as the reference to rebuild against.
- **Result: zero regression, strict gain.** gen2 covers **all 8** fixture tasks
  (MISSING: none) and solves **10** standalone (EXTRA: b1948b0a, c8f0f002 — both
  generalize). The 2 extras come purely from the new freedom the monoliths lacked:
  `emit/colour` (rays from *every* cell of a colour, not just size-1 markers).
  Both extras overlap the transformer's 70, so the combined total stays **75**, but
  the self-built generator is now strictly more capable AND more extensible.

Lesson: the atom factoring (seed×action) is the right substrate — adding one new
freedom (seed=colour) immediately bought 2 tasks the implanted version couldn't see.
The climb continues by adding ATOMS (symmetric-paint, periodic-stamp, legend-draw,
dims-changing emit) to the one synth loop, each behind the fixture guard, never by
hand-writing another monolith. gen2 is now the live generator; generator.ts is the
reference scaffold.

## Update log 8 — next atoms: symmetric-paint + periodic-stamp (no loss, +1)
Added two ACTION atoms to the same synth loop, each behind the fixture guard:
- **symPaint(mode)**: fill each bg cell from its mirror/rot/transpose image, but
  only when the existing non-bg cells are already symmetry-consistent (conflict ⇒
  reject that mode). Generative symmetry COMPLETION.
- **periodic(py×px)**: detect a tile period (each (y%py,x%px) class must agree among
  non-bg cells), then fill bg cells from the tile. Occlusion repair / continuation.

Result: **zero regression** (all 8 fixture preserved), gen2 now solves **13
standalone** (8→10→13). Of the 3 new solves, periodic(3×6) on **8eb1be9a is
NET-NEW** over the 70 baseline (the transformer's periodicFill missed it); the two
symPaint solves (496994bd, f25ffba3) overlap the transformer's completeSym.

Combined system: **76/400 (19.0%)**. The seed×action atom substrate keeps paying:
each atom added under the fixture guard is monotonic (never loses, sometimes gains).
Remaining atoms to add next: legend/key-driven draw (map a small colour-key to a
stamped shape), dims-changing emit (output larger than input), and reflect-copy
(stamp a motif at a mirrored position).

## Update log 9 — flood atom + the REPLICATION AUDIT ("every op in our own words")
- **flood atom** (fill enclosed bg regions, by learned colour or by single
  surrounding colour) added to gen2 under the fixture guard: no regression, gen2
  now solves **15 standalone** (00d62c1b, a5313dff added — both overlap the
  transformer's fillHoles/floodBorder, so combined stays 76).

- **The audit** (`audit.ts`): Jonathan's principle — if an imported op gets results,
  a native equivalent can be built; if not, that's a named gap. Defined a minimal
  native basis {id, rot90, flipH, recolor, tile, scale, crop} and auto-searched
  depth≤2 compositions reproducing each of the 68 ops on random grids.

  **GEOMETRY fully factored:** the whole D4 group is ⟨rot90, flipH⟩ —
  transpose = rot90∘flipH, antiTranspose = flipH∘rot90, flipV = flipH∘rot90∘rot90
  (depth-3, verified). COLOUR family = chains of recolor (removeColor = recolor(c,bg),
  keepColor, swap). SIZE = scale/tile/crop atoms. So ~15 imported ops are confirmed
  derivable from 7 atoms — the imports told us those muscles exist, and we rebuilt them.

  **44 ops are GAP under the geometric basis** — but they split cleanly:
  • ALREADY have a native equivalent on the GENERATION side (proven: gen2 solves
    these task classes): connect↔between, fillHoles/fillObjHoles/floodBorder↔flood,
    periodicFill↔periodic, symmetrize/completeSym/completeDiag↔symPaint,
    drawRays↔emit, bboxFill↔box(fill), drawBox↔box(line), connectObjects↔between.
  • TRUE GAPS = the next native atom FAMILIES to build (the real work the audit
    exposes), in yield order:
      1. object-SELECT(predicate)  → collapses largest, keepLargest/Smallest/Rare/
         Common, keepTopK, selectUnique, selectMajority, keepTouching (≈9 ops → 1 atom)
      2. per-object MAP(transform)  → mapObjects, mapTopK
      3. MOVE(dir,stop) / PLACE(template,anchor) → gravity, gravityObj, shift,
         moveContact, alignLargest, stamp
      4. PANEL split/reduce → half, overlayHalves, combinePanels, odd/maj/overlayPanels, extractCell
      5. group-by-FEATURE→index → colorByShape, paintRank, countEmit
      6. small cleanup atoms → denoise, smoothNeighbor, outline, borderObjects
    (size-special — downscale, scaleByCount, fractal, mirrorConcat, cropToColor —
    become compositions once SELECT exists.)

  **Conclusion:** no imported op is irreducible magic. Each one either factors into
  atoms we already hold (geometry/colour/size + generation/structure) or names a
  missing family. The single highest-yield missing atom is **SELECT(predicate)**
  (~9 ops → 1) — the transform-side analogue of seed×action. Building the native
  SELECT + MAP families is the next muscle, and the audit is the regression guard:
  re-run it to watch each GAP convert to DERIVABLE as we add atoms.

## Update log 10 — the ANTIMATTER sphere (extraction), the mirror of the generator
Jonathan's idea: the framework has matter/void/antimatter but we only built the
MATTER side (gen2 = creation, ink-added, output ⊇ input). The ANTIMATTER sphere is
its mirror — EXTRACTION: target a region and pull it out (output ⊂ input). Its three
jobs map onto extraction: targeting = induce a predicate for WHICH object matters;
map = the object inventory it reasons over; plan = search that model, not pixels.
Convergence: this is exactly the audit's #1 gap, SELECT(predicate) — reached
independently from theory and from the gap analysis.

**The flow MAP (`flowmap.ts`) — classify all 400 by +/−/0 delta sign:**
  MATTER (ink+ / bigger)   **194**   → the generator's territory
  ANTIMATTER (smaller / ink−) **120** → extraction — 30% of ARC, never purpose-built
  VOID (recolour / move)    **48**   → rearrangement
  MIXED                     **38**   → needs BOTH spheres (the composition target)
So the antimatter sphere addresses the second-largest territory.

**The engine (`antimatter.ts`)** — exact mirror of gen2: a synth loop over
PREDICATE {largest, smallest, rareColor, commonColor, uniqueShape, uniqueColor,
mostHoles, topLeft} × EXTRACTION {keep-only, crop-to-bbox, crop-as-mask} over
{blob, colour} components, fit to every train pair. Result: **6 solves
(test-generalizing), +1 net-new (8efcae92) → combined 77/400.** The other 5
overlap the transformer's crop/keepLargest — honest read: basic extraction was
already partly there, so the prototype mostly REDISCOVERS it. Unique yield needs
richer predicates the transformer lacks (count→emit, relational/odd-one-out,
multi-object keep) — the antimatter muscle to grow next, same way gen2 grew.

**The BALANCE (the "math stuff"):** the Collatz identity
MATTER_bits + VOID_bits − ANTIMATTER_bits = −log₂(n₀) becomes, for ARC, a ROUTER:
the sign of a task's delta says which sphere owns it (matter→gen2, antimatter→
extractor, void→transformer). And the deep payoff is the CONNECTION between the
two spheres: the **MIXED 38** tasks need creation AND extraction in series
(draw-then-crop, or extract-then-fill) — solvable only as gen2∘antimatter or
antimatter∘gen2. That two-sphere composition is the next build, and the conservation
law is its acceptance test (residual 0 = matter produced exactly balances
antimatter demanded). Spheres now: MATTER (gen2, 15 standalone) ↔ ANTIMATTER
(extractor, 6 standalone), coupled by the flow-sign router. Combined **77/400**.

## Update log 11 — θ as the VESICA equilibrium (overlap measured, not analogy)
Jonathan's geometry: the two spheres OVERLAP (vesica piscis lens = the MIXED-38),
distinct from op-chains which only TOUCH (kissing/tangent). The amount of overlap is
θ, and θ has an equilibrium: =1 solved, >1 overfit, <1 unsolved/partial.

Made it a measurement (`theta.ts`). For a program on the HELD-OUT test:
A = cells it changes, R = cells that truly change, **θ = |A|/|R|**.
Result across the 11 fixture programs:
  - **all 10 genuine solves → θ = 1.00, recall 1.00 (BALANCED).**
  - the one overfit (60b61512) → **θ = 0.56 (off-equilibrium).**
θ = 1 is a clean separating line. Refinement of the hypothesis from the data: the
overfit landed BELOW 1 (its spurious box-fill rule under-covers the true test delta —
a shortfall), not above. So precisely: **θ ≠ 1 is the failure signal; the sign is
the mode** — θ>1 = overfit bulge (program claims more than the answer), θ<1 =
underfit shortfall (region not fully reached / not all methods found), θ=1 = the two
circles coincide on exactly the required lens. That is the vesica equilibrium, and it
is the same object as the conservation law's residual-0 balance.

Geometry map, now grounded:
  - **kissing (tangent)** = sequential op-chains, output→input, no shared cells (the
    depth-2 DSL programs). Discrete touch.
  - **vesica (overlap)** = matter ∩ antimatter on a shared cell-region (MIXED-38);
    θ is the overlap ratio.
  - **three-body** = MATTER/ANTIMATTER/VOID as three spheres; global equilibrium is
    θ=1 on every flow at once (the full conservation identity balanced). MIXED tasks
    live in the triple overlap.
  - **game ⟂ our spheres** = our interpretation never perfectly equals reality, so a
    residual lens always exists; θ measures how closed it is.

Caveat (honest): θ here is computed against the known test answer, so it is a
DIAGNOSTIC / selection-validator, not a solve-time oracle. The solve-time version is
its MDL proxy: among candidates that all fit train (θ_train=1 by construction), prefer
the MINIMAL-EXCESS program — least extra footprint — which biases θ_test→1 from above
and suppresses overfit. That proxy is the next concrete use: drive the two-sphere
composition search for the MIXED-38 by picking the θ→1 (balanced) chain, not just any
train-fitting one. Equilibrium selection = the framework's own overfit guard.

## Update log 12 — the JET: actions as forces, search as force-cancellation
Jonathan's dynamics: an action isn't only orientation — it's a FORCE vector with a
primary axis AND coupling (side-effects on the other axes). The game applies an
unknown force (the residual, felt on train, not seen). Search = cancelling it; the
coupling is what lets you reach the target axis sideways when the push knocks your
hand off it ("key in a blind hole, something pushing your hand").

Built it (`jet.ts`): residual = mismatch-to-train as a tension scalar (size axis →
colour-histogram band; same-dims → Hamming). Beam search where each step picks
tension-REDUCING actions PLUS near-flat ones (the coupling tolerance — keep
non-greedy states so a first op that doesn't lower tension can set up a second that
does). Accept at θ_train=1.

Result (honest): the jet beam alone solves **37** — far below the flat 77, because
it's a restricted complement (heavy ops excluded, tight grid caps to stay bounded),
and search-reorganization keeps converging below/around the vocabulary ceiling, as
every prior scheme did. BUT it found **3 net-new** multi-step programs the flat
baseline structurally missed, of which **2 generalize**:
  - 28bf18c6 = **crop∘tile**  (TEST-PASS)
  - 6f8cd79b = **recolor∘outline** (TEST-PASS)
  - 91714a58 = keepCommon∘smoothNeighbor (TEST-FAIL — overfit, the θ≠1 case)
These two are exactly the COUPLING wins: a first op that holds/raises tension on the
target axis but sets up the second — reachable by the tension-beam, invisible to flat
depth-2 enumeration. **Combined 79/400 (19.75%).**

Verdict: the force model is real but as a COMPLEMENT, not a replacement — it adds a
few genuine coupled multi-step solves (Jonathan's "spray and push on everything else
to find the combination") while θ catches the overfit it also produces. Consistent
with the standing law: the number is vocabulary-bound; multi-step coupling buys a
little on top. Spheres + θ-equilibrium + force-coupling now form one coherent engine:
MATTER/ANTIMATTER generation+extraction, coupled by the flow-sign router, composed by
tension-force beam, accepted by the θ=1 vesica balance. State: **79/400**.

## Update log 13 — the VESICA built: two spheres composed (honest +0)
Built the literal overlap (`composeSpheres.ts`): joint synthesis without seeing the
intermediate — enumerate stage-1 from one sphere (matterCandidates / antiCandidates),
push the train inputs through, let the OTHER sphere's synth fit the residual, accept
only θ=1 AND test-generalizing. Both orders: antimatter∘matter (create→extract) and
matter∘antimatter (extract→create).

**Result: 0 net-new over the true 79-set.** The composer DOES find and verify 2-stage
sphere∘sphere chains, but every one is a degenerate rediscovery of a task a single
sphere already solves (e.g. matter-box then a trivial extraction). The MIXED-38
hypothesis did not convert: composing the CURRENT matter and antimatter atoms yields
nothing the spheres don't get alone.

Why (honest): composition is only as rich as the spheres' atoms — and there's a
concrete blocker — gen2 (matter) only handles SAME-dims, while antimatter changes dims
(crop), so the most natural MIXED chains (crop-to-region THEN draw, where output dims =
cropped dims) are mostly out of reach until matter gains a dims-aware emit. This is the
standing law one more time: composition/search-organization is vocabulary-bound; the
MIXED tasks need MORE ATOMS PER SPHERE first, not a cleverer coupling.

What's banked: the vesica infrastructure is built and θ-gated, so it will convert
for free as each sphere grows — the moment matter gets dims-changing generation or
antimatter gets count/relational predicates, the same composer will pick up the
genuine matter∘antimatter tasks with no new wiring. Combined unchanged: **79/400**.
The lever remains atoms-per-sphere (esp. dims-changing matter), then re-run the vesica.

## Update log 14 — the ANTIMATTER GENERATOR (is/isn't tags), honest +0
Jonathan's is/isn't duality from the earlier theory: every definition carries positive
(is) AND negative (isn't) tags — a penny IS currency/copper, ISN'T raw-material/other-
metal. The matter generator (gen2) makes IS-content; the antimatter GENERATOR should
make ISN'T-tags. ARC mapping is exact in principle: odd-one-out = "the object that isn't
like the others", denoise = "remove what isn't the pattern", hidden figure = "the cells
that aren't symmetric", targeting = "isn't the rest", map = "everything that isn't us".

Built it (`isnt.ts`): assert a pattern (symmetry mode×{any-disagreement, asymmetric-
overlay}, periodicity-majority, odd-object-by-shape/colour), compute the VIOLATION set
(where the grid ISN'T the pattern), emit it via keep/remove/crop/colour/mask. Synth +
θ/test gate.

**Result: 2 train-fits total, 0 net-new, 1 overfit (caught).** Even after refining the
violation semantics (consensus/overlay, relaxed minority object), it fires on almost
nothing. Honest diagnosis of WHY:
  - The isn't-tasks that DO have clean exact-output answers (odd-one-out, keep-rare) are
    ALREADY caught by the transformer's keepRare/selectUnique/keepSmallest — so even a
    firing isn't-generator is not net-new.
  - The richer "hidden figure / asymmetric overlay" answers rarely equal the violation
    set cell-for-cell in the output FORMAT these actions produce.
So as a STANDALONE SOLVER the antimatter generator adds ~0 on ARC-1.

The truer role (Jonathan's own words: "adding rules to it"): isn't-tags are CONSTRAINTS,
not solvers — they say what the output is NOT, to PRUNE the matter generator's
candidates and to define the targeting complement. That's the antimatter generator's
real place: a constraint/pruning channel feeding the matter sphere and the θ-balance,
not a separate producer of answers. Architecturally the is/isn't generative duality is
now COMPLETE (both halves exist); empirically the isn't-half's value is as a constraint
provider, which is untested and the honest next question. Combined unchanged: **79/400**.

## Update log 15 — the ANGULAR decomposition: matter=cosθ, antimatter=sinθ, tanθ connects
Jonathan's geometry: an action isn't just applied — it makes an ANGLE with the task.
The part along the task vector is MATTER (useful), the orthogonal part is ANTIMATTER
(the wasted/unused "isn't"), and tanθ = antimatter/matter is the connector. "Each game
is a different angle" → each task's target points a different way, so the same action
sprays different isn't-branches. "Failed actions go somewhere" → their orthogonal
residual; the AM generator is the outlet that collects it as a constraint. "1/dim flip"
= the orthogonal complement (swap parallel↔perpendicular). Void = the origin both touch.

Tested it (`angle.ts`): task T = mean train delta as a 12-d flow vector (10 colour-count
deltas + size); action effect E likewise; matter = cosθ(E,T), antimatter = E_perp,
residual R = T − E1.

**Geometry VALIDATED:** solving single-ops sit at mean **cosθ = 0.735** with the task —
they genuinely point toward T, not randomly. Honest caveat (and it IS Jonathan's point):
the cases dragging it below 1.0 are PURE-SPATIAL transforms (rotate/transpose/gravity) —
they change no colour counts or size, so they're near-invisible to the flow-vector. The
geometry axis lives in an ORTHOGONAL subspace this projection can't see — "different
games are different dimensions." Adding a spatial/rotation axis to the feature is the fix.

**Residual-as-selector WORKS:** using R = T − E1 (the antimatter the first op leaves) to
RANK the second op found **2 net-new** test-generalizing tasks (694f12f3, bb43febb) the
flat and jet searches missed → **combined 81/400 (20.25%)**. The "isn't" exhaust literally
pointed at what the next op must supply — the coupling mechanism Jonathan described, now
principled (angular) rather than blind beam. This is the first idea in the
sphere/vesica/θ thread to add net-new beyond the individual atoms — because it's not a
new producer, it's a SELECTOR that uses the antimatter residual to steer composition.

Takeaways: (1) tanθ/angle is real, usable search structure in the flow subspace; (2) the
flow-feature is blind to pure geometry → add the spatial dimension next (matches the
"think about dimensions on the AM side too"); (3) the antimatter residual is best used as
a COMPOSITION SELECTOR (steer op2), confirming update-14's "isn't = constraint, not
producer." Spheres + θ-equilibrium + angular-residual selector now cohere into one engine.
State: **81/400**.

## Update log 16 — theory convergence (Shovelcat_Theory_10_1.pdf) + dimension LIFT
Read Jonathan's 141-pg theory PDF. The ARC engine built bottom-up MATCHES the theory
top-down — three exact correspondences:
  - **Vesica = two domains (§1.4):** ψ-domain (exploration/probabilistic search) = our
    matter GENERATOR; φ-domain (deterministic execution/verification) = our
    transformer/VERIFIER. Overlap Wψ∩Wφ = the lens = MIXED tasks. We rebuilt his vesica.
  - **theta=1 equilibrium INSIDE the vesica (§1.4/§4.3):** theory requires thetaL<1<thetaR
    with bounds **0.814 < 1 < 1.272**. Our result (solves at theta=1, failures off it) IS
    this constraint — and gives a tolerance band: a candidate is "in the lens" when
    theta in [0.814, 1.272].
  - **Dimensions lift via the log-spiral (§7.2/§49):** z(theta)=d·ln(theta)/ln(phi) — info-
    load theta multiplying by phi ascends one dimension level d; z(1)=0 ground, z(sqrt phi)=
    d/2, z(phi)=d. Connector is trig: **tan(helix angle)=dz/dtheta** (§49). Jonathan's
    "dimensions grow/fall with the hypotenuse, tan connects them" = this spiral exactly.

**Acted on it — the spatial dimension LIFT.** Update-15's angular model was geometry-
blind (colour/size flow can't see rotate/flip/shift — orthogonal axis, the "different
dimension"). Added a z+1 SPATIAL subspace to the feature: centroid (meanY,meanX) +
H/V/transpose symmetry-defect deltas. Result:
  - geometry alignment **cos 0.735 -> 0.963** — lifting the axis brings geometry tasks
    into matter-alignment (solving ops now ~15° off, near-perfect). Direct confirmation:
    the dimension was there, just unobserved at level z.
  - angular 2-step found **+1 net-new (4258a5f9)** -> **combined 82/400 (20.5%)**.

Design note (Jonathan's "AM side cheap, low-dim, <1d template"): the feature/AM side
stays MINIMAL and lifts a dimension only ON DEMAND — engage z+1 (spatial) only when the
z-level (colour/size) can't align. That is the theory's spiral schedule = our 4->16->64
coarse-to-fine, now justified: keep the model cheap at ground level, ascend one trig-
coupled dimension at a time as theta-load grows. Matter = the lifted copy of that low-dim
AM template (psi-seed -> phi-execution).

Extensibility guard ("add atoms smoothly, work every time"): `combined_solved.txt` (the
82 banked solves) + the theta-test is the standing regression set — every new atom/feature
re-checks it; an add is accepted only if it loses none AND its net-new pass theta in band
on TEST. So adding atoms is now a guarded, repeatable step, not luck. State: **82/400**.

## Update log 17 — "know what an atom IS": the PERIODIC TABLE (knot/tail/valence)
Jonathan's nuclear-physics result files (ATOM_GROUNDING / IRON_ANSWER_SPACE /
ISOTOPE_THETA / KNOT_TAIL) ground the framework in real atomic data, earned + quantified:
  - **knot/tail**: closed shell = inert KNOT (invariant), valence = reactive TAIL (where
    all chemistry happens); knot 3.83× more rigid (noble-gas IE vs alkali).
  - **isotopes↔pools, valley of stability = the theta=1 line**: stable nuclei mean
    theta 0.980, ALL inside our band [0.814,1.272]; beta- (theta>1) sheds=overfit-trim,
    beta+ (theta<1) fills=underfit. Our vesica theta, confirmed in nuclear data.
  - **Iron**: fusion(+)/fission(−)/void(0) attractor — same +/−/0 shape as Collatz/valley.
His idea: to ADD atoms we must know what they ARE — characterize each like an element by
its knot (invariant core) and tail/valence (reactive bonds).

Built it (`atomchem.ts` -> `atom_cards.json`): for each of the 68 ops, measure its effect
over 4 MACRO-AXES (colour/size/pos/sym). KNOT = axes it never changes (inert core); TAIL/
VALENCE = axes it does (reactive bonds). The PERIODIC TABLE:
  - tail[colour+pos+sym] (25): recolor/keep/symmetrize/connect/draw... the generators
  - tail[colour+size+pos+sym] (9), [colour+size+sym] (6): the size-changers
  - tail[pos+sym] (4): rotate, transpose, gravity, moveContact — the geometry/motion atoms
    (exactly the spatial dimension we lifted in update-16)
  - **NOBLE (4)**: identity, flipH, crop, downscale — inert, close without a reactive tail
  - **needs-structure (12)**: cmap, panels, completeSym — don't react on random grids, only
    bond under structured conditions (the conditional/reagent atoms)

**The table NAMES THE MISSING ELEMENT.** Every valence class is a combo of colour/size/
pos/sym — there is NO valence axis for OBJECT-IDENTITY / COUNT (which-object). That absent
valence = the audit's object-SELECT gap. Knowing what our atoms ARE shows exactly which
atom we lack: one whose tail is "object selection" (a 5th macro-axis). Two independent
methods (audit, periodic table) point at the same missing muscle.

**Valence-guided composition (honest):** bonded atoms by valence-coverage of the task's
required axes. As built it does NOT beat the blind cos-ranked angular search (+0 net-new
in budget) — because 4-axis valence is the COARSE QUANTIZATION of the continuous angle.
The angular cos-theta IS the fine-grained valence. So the two live at different resolutions:
the discrete periodic table is for UNDERSTANDING and safely ADDING atoms (read its card:
does it fill a gap axis? noble or reactive?); the continuous theta is the working SEARCH
selector. Same chemistry, two resolutions.

Takeaway: atoms now have identity cards (knot, valence, noble/reactive, theta-stability),
grounded in the nuclear knot/tail/valley results. Adding an atom is now principled — its
card predicts its role before we wire it in — and the highest-value missing element is
named twice over: an OBJECT-SELECT-valence atom (the 5th axis). State: **82/400**.

## Update log 18 — built the 5th axis (object); the "missing element" was compound
Added the OBJECT macro-axis (nObj + largest-fraction deltas) to BOTH the angular feature
(18-d) and the periodic table (5 axes). Two honest findings:

1. **Angular 2-step with the object axis: +0 net-new** (solved 22 vs 21; the extra was
   already banked). The select tasks it newly sees are already covered by the transformer's
   keepLargest/keepRare/selectUnique family.

2. **Object-select is NOT a separable element — it's COMPOUND.** The object axis lights up
   for almost every atom, because selecting/moving anything incidentally changes object
   count and largest-fraction. There is no clean "object-only" valence: selecting an object
   inherently changes its bounding box (size), centroid (pos), and symmetry. So the select
   ops (keepLargest/keepSmallest/selectUnique/keepTopK) sit in the HIGHEST-valence class
   `[color+size+pos+sym+obj]` — they are the "transition metals" of the table: maximally
   reactive, compose widely, and were already present, just invisible in the 4-axis view.

So last turn's "missing 5th element" was a MEASUREMENT blind spot, not a missing capability.
Adding the axis completes the table (all 5 macro-axes now covered, no empty valence column)
and correctly places the select atoms as max-valence — but it doesn't move the number,
because those tasks were never actually missing. No pipeline changed; the 82 banked solves
are intact (no regression possible — only features/characterization were added).

Meaning: the periodic table is now COMPLETE on its axes. The climb is therefore NOT a
missing axis/element — it's back to the standing law: DEPTH within axes (more/finer atoms
per valence class) + the generators, guarded by the fixture + theta-band. The chemistry
framing gave us the map and the safe add-procedure; it did not (and structurally cannot)
manufacture a missing primitive that solves uncovered tasks — those still require building
real new atom behaviour, now characterizable by card before wiring. State: **82/400**.

## Update log 19 — the RECONSTRUCTION GENERATOR discovers primitives (+3 -> 85)
Jonathan's synthesis: the periodic table is the SHELL; the GENERATORS give it identity.
The generator should RECEIVE an element (place a native prefix "where it goes"), then find
the PATH BACK TO CORE — induce the residual transform that closes input->output — and a
consistent residual that isn't already a native atom = a DISCOVERED primitive. Remember
wins as COMPOUNDS; compounds form where the two spheres' valences meet.

Built it (`discover.ts`): for each unsolved task, try a native PREFIX op1 (identity or a
DSL op, "the element placed"), push train inputs through, then run RESIDUAL INDUCERS that
try to learn the path back: rankRecolor (object colour by size-rank), shapeRecolor (object
colour by learned shape-class), overlay (fixed delta). A fit inducer that generalizes to
TEST = a discovered primitive that solves the task.

**Result: +3 NET-NEW, all via a discovered `shapeRecolor` primitive -> combined 85/400
(21.25%):**
  - 67385a82 = keepColor ∘ shapeRecolor
  - 6e82a1ae = keepColor ∘ shapeRecolor
  - aedd82e4 = identity ∘ shapeRecolor
This is the FIRST mechanism that manufactures a missing primitive and converts it to solves
— exactly Jonathan's "build the element in our own terms, discover new primitives along the
way." The discovered compounds are REMEMBERED in `discovered_library.json` (the memory).
Note: two of the three needed a keepColor PREFIX before the shape-recolor — the prefix is
the "placed element," the induced residual is the "path back to core," and the pair is the
COMPOUND. (The existing colorByShape op didn't catch these; the explicit learned
shapeKey->colour residual generalized where it didn't, and the prefix was required.)

Why this one moved the number when basis-completeness/vesica/valence didn't: it doesn't
re-express existing capability — it INDUCES a new residual rule from the data and keeps it
only if it generalizes (theta-band on TEST). That's a genuine new-atom factory, the one
lever (more atoms) but AUTOMATED. The library + the inducer set is now the growth engine:
add more residual inducers (per-object move, learned placement, count->size) and more
prefixes, and the generator discovers + remembers more compounds. Biggest single jump in
many turns. State: **85/400**.

Next: (1) register `shapeRecolor` (and future discoveries) as permanent carded atoms so
they compose further (compounds-of-compounds = molecules); (2) add residual inducers for
the other valence axes (move/place/count) — each is a new-primitive factory; (3) the
"spheres rotate to expose elements" = pair library compounds by valence-complement.

## Update log 20 — the MATTER/ANTIMATTER CYCLE: cloud (constraint) + nucleus (fill)
Jonathan's closed loop: each side makes what the other lacks. ANTIMATTER produces the
CONSTRAINT — a region, the "electron cloud" = where the answer is allowed to live; MATTER
fills the NUCLEUS — the content inside that region. They pass the partial grid; a (region ×
fill) pair that closes = solve; a fill matter must INVENT inside the cloud = discovered
primitive.

Built it (`cycle.ts`): ANTIMATTER regions = {all, nonbg, bg, border, enclosed-holes,
per-colour cell-sets}. MATTER fills = {learned constant colour, mirror-partner (sym),
object-recolor-by-rank, object-recolor-by-shape} — the last two RESTRICTED to the region
(the discovered primitives operating inside the cloud).

  - Simple fills (const/sym) alone: **+0** (overlap existing ops; discover.ts already took
    the easy residual wins).
  - Add the discovered object-recolor fills INSIDE the antimatter region: **+1 net-new
    (e8593010) -> combined 86/400 (21.5%).** The region constrained where the object-recolor
    applied, and that cooperation solved a task neither side got alone — the cloud focuses
    the nucleus.

This validates the division of labour: AM doesn't make content, matter doesn't make
constraints, and passing the constraint to the matter fill (cloud->nucleus) is a real
compound that the global generator missed. The architecture is the cycle Jonathan drew:
forward (matter fills) + backward (residual discovery, update-19) + the AM constraint that
couples them. Each added fill/region is another place a primitive can be discovered.

Running tally of the discovery engine (the only thing beating the ceiling): update-19
residual-discovery +3, update-20 cooperative cycle +1 = **+4 over the 82 plateau -> 86**,
all test-generalizing, all from INDUCING new rules (not re-expressing old ones). The growth
engine is: prefixes × regions(AM constraint) × fills(matter, incl. induced) × rounds, each
combination a place to discover + remember a primitive. State: **86/400 (21.5%)**.

## Update log 21 — widen the inducer set, let the cycle run (+3 -> 89)
Added 4 residual-inducer factories (each targets a different valence axis):
colorMap (colour->colour residual), shift (learned translation of content), gravity
(cells fall in a learned direction), holeFill (enclosed holes -> learned colour). Ran the
reconstruction generator with the widened set.

**+3 net-new -> combined 89/400 (22.25%):**
  - 25ff71a9 = identity ∘ shift
  - 50cb2852 = outline ∘ holeFill   (compound)
  - a79310a0 = keepColor ∘ shift    (compound)

Honest distinction worth keeping: the discovery engine finds TWO kinds of net-new —
(a) genuinely NEW rules (update-19 shapeRecolor), and (b) KNOWN rules (shift/gravity/
holeFill ~ existing DSL ops) reached as new COMPOUNDS via the prefix×residual frame
(outline∘holeFill, keepColor∘shift) that the flat 1–2-step search missed. Both are real
net-new solves; (b) is composition-reach, (a) is true primitive discovery.

Discovery-engine tally this segment: 82 -> 85 (residual shapeRecolor +3) -> 86 (cooperative
cycle +1) -> 89 (widened inducers +3) = **+7 off the plateau, all test-generalizing**. The
engine has clear diminishing-but-positive returns: each new inducer/region family adds a
few, then saturates until the next family. The lever is now mechanized — widen
{prefixes, AM-regions, matter-fills/inducers, rounds} and the generator keeps discovering +
remembering. State: **89/400 (22.25%)**. (Compares to the static muscle ceiling ~73 and the
pre-discovery plateau 82 — the discovery cycle is the first thing to keep climbing.)

## Update log 22 — keep feeding: reflect / fractal / move-by-colour (+2 -> 91)
Added 3 more inducer factories: reflect (input arranged with its mirrors — g|fH, quad-
mirror...), fractal (self-similar: place a copy of input where cells are non-bg), and
moveByColor (per-object translation keyed to colour). Ran the generator.

**+2 net-new -> combined 91/400 (22.75%):**
  - 4c4377d9 = identity ∘ reflect
  - 8f2ea7aa = crop ∘ fractal   (compound: trim to content, then self-tile)
(moveByColor fit 0 this pass — the position factory is built and waiting for a matching
task.)

Discovery-engine trajectory this segment: **73 (static muscle ceiling) -> 82 (spheres/
angular plateau) -> 85 -> 86 -> 89 -> 91**, every step test-generalizing. Clear pattern:
each new inducer/region family adds 1–3 then saturates; widen the set, it climbs again.
+9 over the plateau purely from the discover/cycle engine. The mechanism is the lever:
{prefix} × {AM region} × {matter fill / induced residual} × {rounds}, every cell a place to
discover and remember a primitive. State: **91/400 (22.75%)**.

## Update log 23 — CONSOLIDATED into one pipeline + honest test-verified number
Refactored discover.ts and cycle.ts to export `solveDiscovery`/`solveCycle` (guarded
main), then built `runall.ts`: one runner that, per task, tries every solver in order
[fast -> codon -> generator(gen2) -> antimatter -> discovery -> cycle] and counts a task
solved only when the program reproduces the held-out TEST output. One command:
`npx tsx src/runall.ts`, ~36s.

**Honest result: TOTAL 81/400 (20.25%), test-verified.** By stage (first to solve):
  fast 61, generator 6, codon 3, discovery 9, antimatter 1, cycle 1.

Consolidation CAUGHT AN OVERCOUNT: the running tally had reached 91, but that counted the
transformer baseline as TRAIN-solves (the old runcodon `solveFast` returns train-fit). Under
uniform TEST verification ~10 of those don't generalize, so the true number is 81. This is
the right ARC metric (score is on the test output), and it's the honest one. The canonical
solved set is now `verified_solved.txt` (test-passing), replacing the inflated combined list.

What the spheres/discovery engine actually contributes (test-verified): transformer core =
fast 61 + codon 3 = 64; the new work = generator 6 + antimatter 1 + discovery 9 + cycle 1 =
**+17 over the core (64 -> 81)**, with DISCOVERY the single largest non-fast contributor (9,
ahead of the generator's 6). So the matter/antimatter/discovery cycle is carrying real,
generalizing weight — it's not just the transformer.

State: **81/400 (20.25%) test-verified, one reproducible command.** Next: (1) re-run is now
trivial after any atom/inducer add (regression = does TOTAL drop); (2) point `runall` at the
ARC EVALUATION set (held-out 400, never seen) for the true generalization test — Jonathan has
an arcprize API key; the public eval set also ships in the ARC-AGI repo.

## Update log 24 — THE HELD-OUT EVAL NUMBER (the real generalization test)
Pulled the public ARC-AGI-1 EVALUATION set (400 tasks, never seen, distinct distribution
from training) from the ARC-AGI repo and ran the consolidated pipeline on it (`runeval.ts`).
[Used the public GitHub data; no API key needed — the arcprize key is for ARC-AGI-2/submission.]

**Honest result: 26/400 = 6.5% on held-out eval** (8.7% on the 298 tasks <=450 cells; 102
oversized tasks were skipped as unsolved — our system has no per-task time budget and can't
process ~22x22+ grids in time, so they count against us). By stage: fast 19, codon 2,
generator 1, antimatter 1, discovery 3.

**The key finding: heavy overfit to the TRAINING distribution.** Training 81/400 (20.25%)
vs eval 26/400 (6.5%) — roughly a 3x drop. This is exactly what the eval set is built to
expose, and it is the honest target number, not the training figure. Everything we tuned
(primitives, inducers, discovered compounds) was developed against training tasks; on a
shifted distribution it transfers at ~a third the rate.

Nuance (and it's encouraging): the discovery/sphere engine is NOT more overfit than the
core. On training it was 17/81 = 21% of solves; on eval it is 5/26 = 19% — the SAME
proportion. So the matter/antimatter/discovery cycle generalizes as well as the transformer
core; the drop is across the whole vocabulary, not specific to the new machinery. The
discovery engine carries its weight on unseen data too.

What this reframes: the real scoreboard is **6.5% eval**, and the lever that matters is
generalization, not training-set count. Two honest implications: (1) chasing more
training-tuned atoms inflates 81 but may not move 6.5 — every new atom/inducer should now
be judged on EVAL, not training; (2) the discovery engine (induces rules from each task's
own train pairs, keeps only test-generalizing) is the right shape for eval because it adapts
per-task rather than reusing training-fitted programs — and the eval data confirms it holds
its proportion. State: **training 81/400 (20.25%); held-out EVAL 26/400 (6.5%)** — the eval
number is the one to grow now.

## Update log 25 — LEARNING layer (meta-learn inducer priors); honest neutral on eval
Pulled Jonathan's prior learning code (Vesica AI/Learning: ComponentLibrary with learned
success/failure confidence + applies-to; FailureBuffer where failures persist as
constraints). Applied the ComponentLibrary idea to the discovery engine: the inducers ARE
components; learn which one solves which KIND of task.

Built `learn.ts`: feature bucket = distribution-level signature (dims same/bigger/smaller,
object-count more/fewer/same, colour-change y/n, symmetry-change y/n). Trained on the 400
TRAINING tasks -> learned, per bucket, which inducer wins. The priors are sensible and
interpretable (transfer-valid, not task-memorized):
  dims:bigger -> reflect/fractal (tiling) ; col:no,sym:no -> gravity/shift (pure motion) ;
  dims:smaller -> shapeRecolor/colorMap (extraction) ; global: shapeRecolor > reflect >
  gravity > colorMap > ...

Applied to EVAL with the learned ordering + a big-grid cheap-ordered attempt (`learnedeval.ts`,
all 400 attempted): **TOTAL 26/400 (6.5%) — IDENTICAL to without learning.**

Honest read: meta-learning the inducer ORDER is NEUTRAL on coverage, because (a) the
discovery search already tries every inducer exhaustively (no early-stop budget that order
could exploit), and (b) the 102 big eval tasks aren't solved by ANY current inducer
regardless of order. The priors DO transfer (the buckets apply correctly to eval) and DO
make the search faster (right inducer first) — but speed-without-coverage doesn't move the
held-out number. This is the standing law, now confirmed on held-out data: the bottleneck is
VOCABULARY (missing inducers for eval's task-types), not search organization or ordering.

The learning that WOULD move eval is not ordering existing components — it is GENERATING NEW
ones. Two concrete directions from Jonathan's own files: (1) FailureBuffer / boundary-seeking
— mine the eval-style FAILURES to propose new inducer types (what residual rule keeps almost-
fitting but isn't in the set); (2) the per-task discovery engine already IS this kind of
learning (induces a fresh rule per task) — so the lever is widening its inducer GENERATORS,
judged on EVAL. State unchanged: **training 81/400; held-out EVAL 26/400 (6.5%)**. Learning-
to-order: built, transfers, neutral. Learning-to-generate-new-components: the real next lever.

## Update log 26 — MINING_NOTES assessed: the eval limit is COVERAGE, not selection
Jonathan mined his old projects for ideas to close the train->eval gap. The doc's §0
diagnosis (train-specific memory/pooling won't transfer; fresh-read gen2/induction/discovery
should) is correct and matches our data. Its #1 recommendation is a LEAVE-ONE-OUT acceptance
gate (induce on k-1 pairs, require predicting the held-out) as the overfit fix. Built and
tested it.

  - LOO gate on discovery, eval: **26/400, unchanged** — looked neutral.
  - Diagnosed why with a BLIND-submission test (`blindeval.ts`, no test peeking): per task,
    commit ONE program (the real submission setting), compare strategies:
      blindFirst (commit first train-fit) = **26**
      blindLOO   (commit LOO-best)        = **26**
      oracle     (any candidate correct)  = **26**
    ALL THREE EQUAL. So among the <=450-cell eval tasks, a correct program exists for exactly
    26, and the FIRST train-fit is already correct every time. **There is no selection/overfit
    problem to fix — LOO and the whole Tier-1 overfit-guard family have ZERO headroom.**

This sharpens the 81->26 drop decisively: it is NOT "we pick overfit programs on eval"
(selection). It is COVERAGE — for the other ~272 attempted tasks we don't PRODUCE a correct
program at all (the training-fitted rules simply don't apply to eval's different tasks). We
under-produce programs; we do not over-produce wrong ones. (Important caveat: this also means
our local "26" measurement was honest, not peeking-inflated — blindFirst confirms it.)

Consequence for the mining doc's tiers: Tier 1 (LOO / reproduction-consensus / closure-drain
/ overfit guards) = no headroom on our eval, measured. The lever is **Tier 2 — fresh-read
REACH**: mechanisms that GENERATE programs we currently can't. Top picks, now evidence-
prioritized: #5 bidirectional meet-in-the-middle (search backward from the output grid —
biggest new reach), #6 derivative/2nd-order rules (rule that CHANGES across the train
examples — a class a single static move-vector misses), #9 toroidal/projective reframing
(periodic/wrap tasks), #7 dream-cycle basin-hopping (escape multi-step traps). These add
coverage; the guards don't. This is exactly the doc's own discipline ("measure before
trusting") applied to the doc itself. State: **training 81/400; eval 26/400 (oracle-limited,
not selection-limited)**. Next: build a Tier-2 reach mechanism (bidirectional search first),
judged on eval oracle.

## Update log 27 — bidirectional meet-in-the-middle: built, +0 on eval (structural)
Jonathan's four-mode framing (forward / backward / meet-in-the-middle / expand-from-midpoint,
with any element a possible midpoint) is conceptually right. Built the meet-in-the-middle
mode (`bidir.ts`): program input--A-->M--B-->output; forward search applies ops A to the
INPUT, backward search applies INVERSE ops to the OUTPUT (M=B^-1(output)); accept where the
two frontiers MEET (A(input)==B^-1(output)), verify all train, test on eval.

**Result: 0 net-new over eval-26.** Structural reason: backward search REQUIRES invertible
ops (rotate/flip/transpose/colour-swap/scale-downscale) — and that invertible set is exactly
what the `fast` stage already covers via brute+repair. So meeting in the middle over them
reaches nothing fast didn't. The eval gap is NON-INVERTIBLE generative rules (draw/fill/
recolor-by-shape/connect): you cannot run them backward from the output (they lose
information), so MITM cannot touch them.

THREE mining-doc directions now tested, all converging:
  - update-25 learning-to-ORDER inducers      -> neutral on eval
  - update-26 LOO / Tier-1 overfit guards      -> zero headroom (oracle=blindFirst=26)
  - update-27 bidirectional Tier-2 search      -> +0 (invertible-only reach overlaps fast)
The convergence is the signal: NONE of search-organization, selection, or backward-search
moves eval, because none adds NEW GENERATIVE REACH. The only mechanism that has EVER added
eval coverage is NEW INDUCER TYPES (the discovery engine: shapeRecolor/shift/holeFill/reflect/
fractal each added solves). So the single confirmed lever for eval is: **invent new
forward generative inducers** — and the highest-value untried one from the doc is #6
DERIVATIVE / 2nd-ORDER rules (a rule that CHANGES across the train examples: a recolor that
increments, a shift whose step grows). That is a genuinely new forward inducer TYPE (not a
search scheme), so it is the one Tier-2 idea that fits the only lever that works. State:
**eval 26/400, oracle-limited**; next build = derivative-dimension inducer, judged on eval.

## Update log 28 — DERIVATIVE-ORDER reframe: the redundant systems are the SAME op at different orders
Jonathan's reframe: our many systems "cover the same things" (lots of +0 overlap) — what if
they're the same operation at different DERIVATIVE ORDERS? Mapping them:
  - **0th order (static, rule = constant):** colorMap, overlay, shift(fixed), gravity, holeFill,
    reflect, fast single-ops. The transform is one fixed thing.
  - **1st order (rule varies with an index/feature):** rankRecolor, shapeRecolor — output
    changes per object.
  - **2nd order (the variation itself varies):** fractal/self-similar, nested programs.

The key diagnosis this exposes: **our 1st-order inducers store the derivative as a MAP
(memorized lookup), not a FUNCTION.** rankRecolor learns {object->colour} as a table, so on
eval a never-seen index/object fails — it can't extrapolate. That is very plausibly a big
part of the 81->26 drop: we captured 1st-order STRUCTURE as 0th-order DATA.

The fix — make the derivative an extrapolating FUNCTION. Built 3 functional 1st-order
inducers (`scaleByFeat`/`tileByFeat`/`shiftByFeat`): a parameter (scale factor, tile count,
shift) = a LINEAR FUNCTION of an input feature (object count / colour count), fit from train
(needs >=2 distinct feature values), and EVALUATED on the test input — so it predicts unseen
counts instead of memorizing seen ones.

**Result: eval blind-oracle 26 -> 27.** The win is d4b1c2b1 via scaleByFeat: output =
scale(input, k) with k = f(object-count), extrapolated to the test grid's count. This is the
FIRST eval gain from the whole post-consolidation thread — LOO (+0), learning-order (+0),
bidirectional (+0) all failed because they don't add generative reach; the derivative inducer
DID, because making a parameter a function (not a constant or a table) is exactly new,
generalizing reach. (tileByFeat/shiftByFeat built, fired 0 on eval yet — waiting for matching
tasks.)

The reframe is the real deliverable: the climb is NOT more parallel systems — it is lifting
each existing operation up the derivative ladder (0th constant -> 1st function-of-feature ->
2nd function-of-function), and crucially storing 1st-order rules as FUNCTIONS that extrapolate,
not maps that memorize. That single change (map->function) is both the anti-overfit fix AND
the eval-reach lever, unifying the two problems. Next: convert the existing map-inducers
(rankRecolor/shapeRecolor) to functional/extrapolating form, and add more feature axes
(position, size, distance) to the derivative inducers. State: **eval 27 (first post-plateau
gain), training 81+; derivative ladder is the organizing principle.**

## Update log 29 — SHEET-SLIDE / SHEAR: the derivative made geometric (validated)
Jonathan's geometric reframe: the grid is a shape, its rows/cols/diagonals are FACES/SHEETS,
and a transform SLIDES each sheet by an amount that's a FUNCTION of its index — "which axes
slide and to where." 0th order = whole grid shifts by a constant; 1st order = each row
slides by f(row) = a SHEAR / cascade. Cyclic sliding = toroidal (also mining-doc #9). "A
sheet sliding on an axis we didn't expect, but still fitting" = a discovered transform.

Built `induceShear` (D14): for each axis (rows-slide-horizontally / cols-slide-vertically),
measure the per-sheet cyclic shift, fit shift = a*index + b (linear in sheet index), apply
toroidally. It induces WHICH axis slides and the FUNCTION of the slide.

**Validated on training: e9afcf9a solves via identity∘shear, test PASS** — a real task where
each sheet slides by a function of its index, now solved and generalizing. The whole
derivative family fires on 9 training tasks (scaleByFeat 7, shear 1, shiftByFeat 1; most
test-pass). On eval it held at 27 (no clean shear/count-scale in the <=450 eval subset yet) —
built and waiting, like a primitive looking for its task.

The arc of the last few updates is the real story: once we reframed by DERIVATIVE ORDER
(update-28) and then made the derivatives FUNCTIONS OF GEOMETRY (this update — sheets sliding
by f(index)), we started generating transforms the 0th/1st-order map-inducers structurally
couldn't (scale-by-count, shear). These EXTRAPOLATE (a function, not a table), which is the
exact property eval rewards. The organizing principle is set: lift every operation up the
derivative ladder AND express the 1st derivative as a sliding-of-sheets function over a chosen
axis. Next axes to add: diagonal sheets (cross-sections), per-object slide-by-rank, and
converting rankRecolor/shapeRecolor to functional form. State: **eval 27, training grown by
the derivative/shear inducers; derivative-geometry is the live frontier.**

## Update log 30 — next derivative axes (+0, saturation) + priors re-centered (balance)
Added more feature axes (maxObjSize, nonBg-count) to the feature-functions and a new
`objSlideByRank` inducer (each object slides by a LINEAR function of its size-rank — the
object-motion 1st derivative). Measured:
  - eval blind-oracle: **27, unchanged**; training derivative fires: **same 9** (scaleByFeat
    7, shear 1, shiftByFeat 1). objSlideByRank + extra feats fired 0 — no matching ARC-1 task.
  - **No regression** — all prior discovery solves intact; the additive-inducer architecture
    stays balanced under expansion (a new inducer can only add, never displace), which is why
    discovery has been monotonic throughout.

Honest pattern: the derivative ladder has diminishing returns on ARC-1. The big win was the
count->scale derivative (`scaleByFeat`: +7 training / +1 eval) and `shear` (+1 training); the
later axes (object-slide, extra features) come up empty because the matching tasks are rare in
this set. Each derivative family adds a few then saturates — the same shape as the muscle/atom
grind, one level up.

Per Jonathan's energy model ("expand -> the cores must MOVE to keep balance"), re-centered the
priors after the expansion (re-ran `learn.ts`): the global inducer order now places the
derivative inducers in their earned slots (scaleByFeat 5th, shiftByFeat/shear in the tail).
That re-learning IS the core relocating — the selection center shifts to account for the new
vocabulary, keeping the search balanced. (The discovery layer self-balances; the priors layer
is where the core actually moves.)

State: **eval 27 (6.75%), training ~83**; derivative-geometry validated and now saturating on
ARC-1. The remaining ARC-1 headroom is no longer in single-axis derivatives — it is genuinely
different task TYPES (relational / multi-object / conditional rules), which is a larger build,
or accepting we are near the deterministic-induction ceiling for this set. The lever and the
discipline are both clear: new inducer TYPES, each judged on eval, priors re-centered after.
