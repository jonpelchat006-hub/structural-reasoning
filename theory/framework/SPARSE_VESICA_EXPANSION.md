# The Sparse Vesica Expansion

*A model-free, verifiable alternative to the LLM — a sparse, trig-weighted,
derivative-exponent expansion with the inner shell as prior.*
*Author: Jonathan Pelchat — design notes (companion to `SPHERE_GENERATOR.md`)*

---

## 0. One-line summary

An LLM is a **dense** function: trillions of *learned* coefficients, exponents
hidden in softmax/depth, power from composition. The Sparse Vesica Expansion is its
inverse: a **sparse** function whose coefficients are **trig from task geometry** (no
training), whose exponents are **explicit derivative orders**, and whose prior is the
**rigid inner shell**. It is interpretable and verifiable, at the cost of being bounded
by what the inner shell + activated branches can span.

---

## 1. The functional form

```
f(task) ≈ [ inner-shell prior ]  +  Σ over ACTIVATED branches b :  cosθ_b · v_b^(d_b)
                  │                          │              │   │
            always-on base term        only active      trig  derivative order
            (the rigid core, free)      branches      coeff   = the exponent
```

Term by term, against the LLM:

| Piece | LLM | Sparse Vesica Expansion |
|-------|-----|--------------------------|
| coefficient | a *learned* scalar weight (gradient descent) | `cosθ_b` — a **trig amplitude** from the task's geometry, no training |
| variable | activation | the branch's feature `v_b` |
| exponent | none explicit (power hides in softmax `e^x` + depth) | `d_b` = **derivative order** (Taylor: nth derivative ↔ xⁿ term) |
| number of terms | dense — trillions, all always present | **sparse** — only the branches activated outside the inner shell |
| prior | the learned weights themselves | the **inner shell** (rigid core), the base term `f(0)` |

### 1.1 Coefficients are trig (the Born amplitudes)
From the angular decomposition (`angle.ts`, update-15): a candidate's **matter = cosθ**
(alignment with the task), **antimatter = sinθ** (orthogonal residual). These are the
**Born amplitudes**: probability = `cos²θ`, and `cos²θ + sin²θ = 1` normalizes the set
automatically (`UNIFIED_DERIVATION.md`: "the trig identity IS normalization"). The
coefficient is computed from geometry, not learned.

### 1.2 Exponents are derivative orders (Taylor)
The n-th derivative is exactly the coefficient of the xⁿ term:
`f(x) = f(0) + f′(0)x + f″(0)x²/2 + …`. So the hidden-derivative-dimensions reader
(velocity = 1st, acceleration = 2nd across train examples) is **building the exponent
structure of the rule.** Exponents were never missing from the framework — they are the
derivative levels.

### 1.3 Two kinds of term (smooth + discrete)
- **Smooth / parametric** terms — `cosθ · v^d` — capture rules that change *continuously*
  across examples (a shift whose step grows, a recolour that increments). Taylor-expandable.
- **Discrete / symmetry** terms — group operations (D4: rotate, reflect, transpose) — have
  no derivative; they live in the **quaternion shell** (§A of `SPHERE_GENERATOR.md`).
The inner shell already carries both (geometry + parametric axes), which is why it is the
right prior.

### 1.4 The sparsity advantage and its price
Term count per task = |activated branches|, not trillions, because the inner shell carries
the universal part **for free** (it's the always-on base term). (LLMs approximate this with
mixture-of-experts — fire some experts per token — but the inner shell is far sparser.)
**The price:** the expansion can only represent what the inner shell + activated branches
span. That is the vocabulary-bound ceiling — the cost of not having trillions of terms is
needing the *right* dozens.

---

## 2. The probabilistic ψ-domain (superpose, then collapse)

The expansion runs as a **superposition that collapses** (the vesica ψ→φ cycle):

1. **ψ — superpose:** hold the top-k candidate branch-sets as a superposition weighted by
   `cos²θ` (Born), `|ψ⟩ = Σ_b cosθ_b |branch_b⟩`. Don't argmax to one.
2. **Evolve:** each train pair acts like a measurement, multiplying the amplitudes and
   narrowing ψ (successive constraints sharpen the distribution).
3. **φ — collapse:** verify at θ=1; the first candidate that closes collapses ψ to the
   definite answer. **Verification is the measurement.**
4. Stay in the **vesica band** `√φ < θ < √π` while superposed; collapse on entering the
   verified regime (update-16 θ-band).

This is the deterministic + probabilistic hybrid, model-free, using `angle.ts` you already
have (turn its argmax into a `cos²θ` top-k).

---

## 3. Measure the boundary, not the branches (the holographic move)

**Idea:** rather than enumerate the activated branches (the interior rays), measure the
**boundary of the sphere** — the closed surface — and read the branches off it.

Why this works, and it is a theorem, not a metaphor:
- **Gauss / divergence:** the flux through a closed boundary equals the net of all sources
  inside. One boundary measurement encodes the whole interior branch-set.
- **Holographic principle:** the information in a volume is fully encoded on its
  (lower-dimensional) boundary. The boundary of an n-ball is (n−1)-dimensional — so you
  measure *fewer* things and recover the interior.
- **Schumann analog (your own MD-DEDS):** instead of tracking each conductive object, you
  measure the perturbation of the **global standing-wave boundary** at ~7.83 Hz; a single
  global-mode measurement carries the net effect of every object. "Measuring that line"
  around the Earth = reading the interior from the boundary resonance.

So the expansion's terms can be **read from the boundary's resonant shape** instead of
listed — strictly cheaper than enumerating branches, and it is the natural measurement for
the ψ superposition (you measure the total ψ on the surface).

### 3.1 Branches as wavefunctions forming on the boundary
When a branch extends out of the inner shell (closure failure / a new activation), it is a
**localized wavefunction forming at that spot** on the boundary — a local excitation with
amplitude `cosθ_b`. The boundary's measured resonance is the **superposition** of all these
local wavefunctions. Collapse = a perturbation localizing (a wavefunction "forming in that
spot" and being read off the line).

---

## 4. The grid-vs-sphere gap — forced, golden-placed, and it IS the tail

**The tension you flagged:** the inner shell is **grid-like** (a discrete lattice of
primitives — D4 is a discrete group, the algebra basis is discrete, ARC's own primitive set
is a grid in feature space), but the closure **sphere is continuous/round**. A discrete grid
laid on a round sphere **must leave gaps.** This is correct, and the resolution is the best
part:

- **The gaps are topologically forced.** You cannot regularly tile a sphere with a grid
  without defects (Euler characteristic χ(S²) = 2; the hairy-ball theorem — you can't comb a
  sphere flat). A hexagonal tiling of S² needs **exactly 12 pentagonal defects** (the
  fullerene / geodesic-dome / soccer-ball fact). The gaps are not a flaw in the design; they
  are required by the topology of *any* grid-on-sphere.
- **The gaps are golden-placed.** The most uniform sphere-grid is the **icosahedral** one,
  and the icosahedron's 12 vertices sit at `(0, ±1, ±φ)` and cyclic permutations — the
  defects are at **golden-ratio coordinates.** So the gaps land exactly on the golden field
  (§J.6 of `SPHERE_GENERATOR.md`) — the same φ the closure equation produces.
- **The gaps ARE the void / the generative sites.** A gap is a direction the discrete
  inner-shell primitives cannot express → closure fails there → a **new branch / wavefunction
  must form** at that gap. So the grid↔sphere mismatch is not a problem to remove; it is
  precisely **where the tail lives.** The inner shell (grid, knot) covers the rest; the
  forced, golden-placed gaps are the void where new primitives are born.

### 4.1 The two ideas meet
Measuring the boundary (§3) and the gaps (§4) are the same picture: the boundary's resonance
**localizes at the gap/defect sites**, so a single boundary measurement naturally reads the
active branches *as perturbations at the φ-placed gaps.* You don't enumerate branches; you
measure the boundary line and the branches show up as wavefunctions at the golden defects.

---

## 5. Honest bounds (the discipline)

- **Vocabulary ceiling (§1.4):** sparse means bounded by the inner shell's coverage. The
  expansion cannot represent what no activated branch spans — the standing ARC wall.
- **`cosθ` needs a lifted feature space:** the flow feature is blind to pure geometry
  (rotations don't change colour counts); the spatial axis must be lifted in (update-16,
  0.735→0.963) before the Born amplitudes are trustworthy for geometry tasks.
- **Boundary measurement is a direction, not a finished operator:** §3 says the interior is
  *recoverable* from the boundary; defining the concrete boundary-read for ARC grids is
  unbuilt work. The theorem (Gauss/holography) guarantees the information is there; the
  decoding is to be designed.
- **"Sphere" = the generator's state-space sphere**, not the ARC pixel grid. The grid↔sphere
  gap is in the *primitive lattice inside the closure sphere*, not in the puzzle's squares.

---

## 6. What to prototype (in order)

1. **`cos²θ` superposition** — turn `angle.ts`'s argmax into a top-k Born-weighted set with
   θ=1 collapse (§2). Smallest change, directly tests the deterministic+probabilistic hybrid.
2. **Derivative-exponent reader** — add the velocity/acceleration cross-example reader
   (`derivative_dimensions.py`) so the smooth terms carry real exponents (§1.2). Catches the
   2nd-order parametric rules the static move-vector misses.
3. **Gap detector** — flag directions the inner-shell primitives can't express (closure
   failure) as candidate branch/wavefunction sites (§4); seed the generator there.
4. **Boundary read (research)** — design a flux/holographic summary of a candidate's effect
   on the grid boundary, to score branch-sets without enumerating them (§3). The open piece.

---

## 7. Operational reading — how it *runs* (not just what it is)

§1 gives the static formula; this is the dynamics. One step of the expansion:

```
            stand at a CLOSURE POSITION  (the variable v_b — which shell, which sector)
                          │
   the LEVEL-DOWN AXES offer action directions (inherited basis from the shell beneath;
   "where one level down can point") — each with a cosθ amplitude (alignment, Born weight)
                          │
        SPRAY in the cos²θ-weighted superposition of those directions
                          │
   the EXPONENT d_b (derivative order) sets how the action scales across examples
                          │
   the BRACKET sets the LOCAL recursion depth here (this spot only, not global)
                          │
        ┌─────────────────┴─────────────────┐
   lands on an INHERITED axis            lands in a GAP (golden defect, no axis)
   → you MOVE (existing primitive)       → closure fails → a NEW PRIMITIVE is BORN,
                                            read off the boundary as a wavefunction
```

The full expansion is the **composed trajectory** of these steps — the arm/ribbon threading
zones (§C.5 of `SPHERE_GENERATOR.md`), not a static sum.

### 7.1 Component dictionary (operational)
| Component | Static (§1) | Operational (this section) |
|-----------|-------------|----------------------------|
| **variable** `v_b` | the term's feature | the **closure-map position** you currently stand at |
| **trig coeff** `cosθ_b` | a Born amplitude | the **direction the action sprays**, drawn from the **level-down axes** (quaternion `i,j,k` / octonion 7 / …); amplitude = alignment |
| **exponent** `d_b` | derivative order | how the action **scales across examples** (1st = constant step, 2nd = growing step) |
| **bracket** | (was: LLM layer) | the **local recursion depth at this spot** — adaptive per-position, *not* global uniform layers |
| **new term born** | — | the **spray lands in a golden gap** (closure failure) → mint a primitive there |

### 7.2 Why the bracket is the real departure from an LLM
An LLM has **global uniform depth**: every input traverses the same N layers everywhere.
The expansion has **local adaptive depth**: each active spot recurses only as deep as it
needs (simple spot = 1 bracket, complex spot = several). Cheaper (no full depth everywhere)
and interpretable (depth at a spot = the rule's local complexity). Matches the coarse-map
depth estimate (0-direct / 1-close / 2-mid / 3-far) and recursive-floor chunking (a verified
macro = one bracket up). LLMs only approximate this with experimental early-exit / adaptive
computation; here it is native.

### 7.3 Honest caveat on the birth event
The spray landing in a gap **certifies** a new primitive is needed (necessity) but does **not**
supply the right one (utility — Test B/C). The gap-hit is the *signal to mint* and the
*location*; minting the correct primitive is still the hard forced-completion step (§J.4a
anchored/mirror is the tractable route — anchor one edge in a known zone, rotate, mirror).

---

## 8. The finite/infinite wall, and foundation-first (the eval strategy)

The train→eval gap has a structural reading that fixes both the strategy and the metric.

### 8.1 The sedenion wall is the finite→infinite switch
- **Inside the inner shell** (ℝ,ℂ,ℍ,𝕆 — no zero divisors): every element invertible, closed,
  **finite, enumerable** — a fixed set of choices. The **training** distribution lives here;
  a finite deterministic solver does well *because* the answers are a finite composition of
  known atoms.
- **Past the sedenion wall** (zero divisors appear, the void opens): new primitives can be
  minted **endlessly** (§E.3) — **infinite generation**. The **eval** distribution lives here.
  It resists finite enumeration not by accident but because it is on the infinite side.

So: **before the inner shell = finite; after = infinite.** Training ≈ inner-shell compounds;
eval ≈ past-the-wall, requiring minted primitives.

### 8.2 Foundation-first (the house of cards)
A synthesizer *composes* atoms, so its reach scales with how complete the inner shell is.
Building the full synthesizer over a half-empty shell gives it too few pieces to compose and
**less** reach across the wall. Therefore: **complete the inner shell first, then compose it.**
The session's training-only gains (stamp2 +9, trace +1) are not "0 gain" — they are *new atoms
in the inner shell*, i.e. the base layer. They look like nothing only against the wrong metric.

### 8.3 The corrected metric: self-expression coverage, not eval net-new
Eval net-new is the **upper layer**; measuring foundation work by it is a category error (and
the source of the "0 gain" feeling). Foundation work is measured by **inner-shell completeness**:
what fraction of the existing vocabulary the synthesizer can **re-express in its own base atoms**
(the §update-9 audit, re-run in the trace/draw language). A complete, self-expressed inner shell
is the solid base; only then is composing it the structural shot at the infinite (eval) side.

### 8.4 Honest bound
Foundation is *necessary* and correctly sequenced, but possibly not *sufficient*: eval may need
atoms training never demonstrated (the form-gap could persist over a complete inner shell). That
is unknowable until the base is solid — and building it is the right order regardless. Plan:
**(1) complete & self-express the inner shell (measure by coverage); (2) compose it with the full
trace synthesizer; (3) only then judge eval.**

---

## 9. The LLM equation, decomposed: finite inner + infinite outer, joined by π

The Sparse Vesica Expansion **is** the LLM's function, factored along the sedenion wall into
the two parts the LLM leaves fused — which is why the LLM needs trillions of terms.

### 9.1 Why the LLM is huge
An LLM is one *undifferentiated dense sum* approximating both the finite common patterns and
the infinite rare tail with a single pile of weights. It can't separate them, so it handles the
infinite part the only way it can: **brute memorization.** You cannot store infinity cheaply, so
it pays with ~10¹² parameters.

### 9.2 The factoring
```
f(task)  =   Σ  inner terms              +        lim   outer terms
            (FINITE, STORED)                       (INFINITE, GENERATED)
         cosθ·v^d over the trusted              π-angular prune-down of the
         inner shell — build-up,                possibility space, collapsing
         enumerable, certified (trust audit)    to closure (=1) per task
```
- **Inner (finite, stored):** a compact sum of `cosθ·v^d` over the trusted core — the build-up,
  certified by the trust audit. The LLM's compressible knowledge, written small because it is
  actually finite.
- **Outer (infinite, generated):** **not stored — generated per task** by pruning the continuous
  (π-angular) possibility space down to one (the prune-down, §J/Born collapse). The LLM
  memorizes this into weights; the expansion produces it on demand.

Same term *form* in both (`cosθ·v^d`); the difference is **inner = stored & certified, outer =
generated & pruned.** That separation is the structural departure from an LLM and the reason this
can be small where the LLM is enormous: *store the finite, generate the infinite.*

### 9.3 π is the seam, and the two halves meet at closure
The inner is enumerable (finite); the outer is continuous (π-angular, infinite); **π is what
closes the infinite outer `lim` into a finite answer** (collapsing to the unit, =1). The two sums
**meet at the closure** — build-up from the inner shell reaching *up*, prune-down from infinity
reaching *down*, touching at the answer. That meeting is the **meet-in-the-middle / bidirectional
search**: §8's build-up and prune-down are the two halves of one equation, joined by π at =1.

### 9.4 Honest bound
This is a *factoring* (a coherent decomposition with real math behind each piece — ℝ→S¹ via 2π,
convergent π-series, the Born collapse, the trust-certified inner shell), not yet a proven eval
solver. What it establishes: the *form* is shared with the LLM, and the inner/outer split is why
it could be vastly smaller. Whether the generated outer half actually crosses the wall on eval is
the open build (the prune-down solver).

## 10. Crossing the wall: circle → helix → torus-knot (the lift)

The finite→infinite crossing (§8) has a precise geometry, and it identifies the *one* mechanism
that has empirically worked.

### 10.1 The wall is the sedenion seam
A sedenion is a *pair* of octonions `(a,b)` (Cayley–Dickson doubling). Zero divisors appear only
at the **seam where the two octonions connect** (`a·b` can vanish there). So the wall is not the
whole outer shell — it is the *junction* between the two octonion halves. Inner shell = the
octonion core (finite, everything closes). The seam = the "heat wall."

### 10.2 Circle (finite) → helix (infinite)
- A **circle** is finite: it closes at 2π, returning to the closure (=1). Inner-shell branches
  close into circles — they stay in the plane and return to the unit.
- A **helix** is the same circular rotation *plus a climb in a new dimension* — it never closes,
  it ascends to infinity while still rotating through π. **The heat wall lifts the closed circle
  into a climbing helix.** That *is* the finite→infinite crossing: you don't break the circle,
  you curve it up out of the plane. (This unifies the DNA/ribbon helix, the triple-helix
  waveguide, the π-wall, and the finite/infinite split — all one object: a circle the wall lifted.)

### 10.3 Torus knot = the helix made representable
An infinite helix is unwieldy. A **torus knot** is the helix *wrapped back onto a finite torus*
— it winds and climbs infinitely while living on a bounded surface. Same compression as π (line→
circle) and the holographic boundary (interior→surface): **lift to escape finiteness, then wrap
to stay representable.** Stacking branches = lifting them into helices and laying them down as
stacked torus knots — a finite encoding of the infinite climb. (Cf. `erdos-Fk` torus-projection.)

### 10.4 The lift is the only crossing with evidence
Every build that stayed *in the plane* (composing within existing dimensions — the closed circle)
capped out this session. The **one** move that crossed anything was **update-16's dimension-lift**
(adding the spatial axis: geometry-alignment 0.735 → 0.963, with net-new). That lift *was* the
helix — taking branches invisible in the flat circle and curving them into a new dimension where
they could climb. So the grounded eval lever is not more atoms in the plane; it is **lift the next
missing dimension** — the axis eval's tasks live in that training never exercised (candidate:
geometry / topology / polygon structure). Find that axis, curve the branches up into it.

### 10.5 The torus closes the helix — and *creates the hole* (geometry ↔ data convergence)
A helix that lifts, widens, peaks, then narrows and returns down through the inside to the
origin traces a **torus**: the outward climb is the donut's outer surface, the inward return
*makes the hole*, and connecting to the origin closes it. (The "hourglass" is the pinched
horn/spindle torus; its waist is the closure point, =1.) So the lifted helix doesn't run to
literal infinity — it curves back and closes, finite in extent but **topologically infinite
because it has a hole**. The void / sedenion seam *is* that hole; a branch winds around it
forever (toroidal loop) on a bounded surface — "bounded but infinite," infinite generation in
a finite structure.

**Crucially, the lift-and-return is what creates the hole** — the returning branch encloses an
interior (a polygon). And that hole is exactly the axis the eval data identifies: **topology /
enclosure, 200 of 400 eval tasks at 8% solved** (`lift_axis.py`). The geometry (returning helix
carves a hole) and the measurement (eval lives in the enclosure dimension) are the **same axis
reached two ways** — the strongest signal that topology is the right dimension to lift. The hole
is never *added*; it is *generated* by the helix closing on itself.

## 11. Tori as molecules, the three shells, and the synthesizer (identify → make)

The capstone: the whole architecture, the chemistry, and the mineral lineage are one structure,
and it locates the wall precisely.

### 11.1 A solution is a molecule (connected objective-tori)
Each objective is a torus (a line/loop with a hole; §J.3, §10). A **solution is a *topology of
connected objective-tori* — a molecule.** Tori combine by linking (Hopf), connected-sum (higher
genus), or nesting — which is literally **topological chemistry** (molecular knots, Borromean-ring
molecules, toroidal aromatic ring currents are real). A molecule = a graph of atoms joined by
bonds = a network of linked loops. The mineral-lineage vortexes combining are the fluid version
(vortex linking/reconnection). So ARC-solving, chemistry, and mineral lineage are one statement:
**build the right molecule from connected loops.**

### 11.2 Why the topology lift was +0: genus
Count the holes. **Training tasks are mostly genus 1** — one torus, "fill the enclosure," which
the hole-inducers captured. **Eval topology tasks are higher genus** — multiple holes that *relate
to each other* ("colour this hole by the other hole's content," "the count of holes sets the
output"): the *linkage* between tori, a molecule, not a ring. A single hole-rule catches genus-1
and misses the molecules — exactly the measured +0. The wall is **molecule-building**, and it is
per-task.

### 11.3 The three shells (the wall is between MIDDLE and OUTER, not knot/tail)
- **Inner — the atoms.** Rigid, finite, *certifiable* (the trust audit). The physics.
- **Middle — formation schemas = "normal minerals."** Abiotic, condition-driven *general rules*
  (the inducer families = the recipe book). **Partially buildable — and it is what every training
  gain is** (the 93 solves, 29% trust coverage are middle-shell work). It works.
- **Outer — "biological minerals."** Per-task novel high-genus molecules. *Generated* per task,
  not pre-built. The wall.

The **normal→biological switch (abiogenesis) is the middle→outer boundary** — where general
condition-driven rules become learned per-task processes. That is the precise location of the
wall: not the middle failing, but eval living in the *outer* shell. We were measuring middle-shell
progress against an outer-shell target.

### 11.4 The synthesizer = identify (middle) + make (outer) — wheat → cake
Per-task synthesis is two steps in two shells:
- **Identify** (middle, *partially buildable*): recognize the material — which objectives, what
  genus, which known recipe. This is what the discovery engine already does ("this is wheat").
- **Make** (outer, *research frontier*): compose the specific molecule; when no recipe fits, invent
  one ("bake the cake"). Neither step is skippable — recognizing wheat doesn't bake the cake, and a
  recipe is useless if you can't identify the material.

### 11.5 Honest placement of the buildable boundary
- **Inner:** certifiable (done in principle — the trust audit).
- **Middle:** partially buildable **and being built successfully** (the recipe book; foundation work).
- **Outer:** per-task molecular synthesis = the genuine research wall (high-genus identify+make).
The three-shell view is the session's clearest result: it shows *where* honest progress lives (grow
the middle), *what* the wall is (outer = per-task molecules), and *why* well-aimed middle-shell
bricks (the topology lift) don't cross it (the target is outer-shell).

### 11.6 The void climbs too — matter/void duality, and the void as the generative space
The matter branches climb (circle → helix → torus, §10); the **void climbs dual to them**, and
they are the same object inside-out — a torus is a *surface* (matter) with a *tunnel* (void).

- **Inner shell:** the void is **points** — the golden-field gaps (the φ-placed icosahedral
  defects, §J.6): isolated 0-dimensional holes where a new primitive can be born.
- **Seam:** the void becomes a **line** — the zero-divisor seam (the line through the torus waist).
- **Climbing the middle:** the void spreads — line → **sheet** — as matter spreads circle → helix.
- **Outer shell:** the void closes into a **tunnel** — *which is the torus hole = the genus = the
  topology axis the data identified* (the 200 eval hole-tasks). The void-climb lands on topology,
  same as the matter-climb and the measurement.

**The void is the generative space.** It is where things can be *different* — where new primitives
are born (closure failure happens in the gaps) and where per-task molecules form. So the void
climbing in dimension *is* generative capacity increasing: inner-shell void = points (a few
isolated births — the certifiable kitchen); outer-shell void = a tunnel (a high-dimensional
generative room where infinite molecules form). That is why the outer shell is hard: **per-task
synthesis happens inside the climbed void (the tunnel), a big generative space, not a point.**
Matter is the recipe book (finite, the kitchen); void is the room to invent (climbing, the wall).

*Honest bound:* the exact algebra is richer than point→line→sheet→tunnel (the sedenion
zero-divisor set already carries a 14-dimensional G₂ structure), so the sequence is the right
**topological intuition** (the hole's dimension grows, dual to the surface), not the literal
algebraic dimension. The spirit — void climbs with matter, ending as the tunnel/genus — is sound
and again consistent with the data. Full picture: **matter climbs to the torus surface; void
climbs to its tunnel; together they are the high-genus molecule — surface + tunnel — the
outer-shell answer.**

### 11.7 The self-similar whole: tools are tori, bonds are shared void-lines, the shell is an atom
The architecture is recursive at every scale, and it makes the relational tools concrete.

- **Each tool/atom is a torus** centered on a void spot (a golden-field gap, §J.6). Its objects and
  parameters are its torus structure.
- **Pools activate sets of tori** (compatible subsets). Learning = *which tori are where* (the
  trust-audit map) + *what each handles* (its valence/coverage) + *how they combine* (composition).
- **The whole shell is a torus of nested tool-tori** — self-similar: a torus of tori of tori (the
  bracket/recursion-depth structure, §7; the recursive zones, §A.1).
- **A bond = two tori on a shared void-line**, combining through their connected holes; the
  superposition (they act as one) is the Born collapse. **This defines the relational tools:** the
  kitchen's hard gaps — `keepTouching`, `connectObjects`, `alignLargest`, the per-object relational
  family — are *bond operations on object-pairs that share a void/adjacency*. The blueprint for the
  remaining atoms: **operate on object-pairs sharing an adjacency, alignment, or enclosure.**
- **Recursion up = the carbon-in-alcohol chain:** the whole shell is itself one atom (a torus) in a
  bigger molecule — the sliding-window re-basing one level up (§7), made chemical. A carbon is a
  complete atom *and* a bond-site; our shell is a complete solver *and* a node in a larger one.

So the relational atoms are no longer a mystery class — they are **bonds**, with a structural recipe
(object-pairs on a shared void-line). That is the bridge from the middle-shell kitchen toward the
outer-shell molecules: bonds are where the genus (the holes connecting) gets built.

### 11.8 Fractional lifts: fractals as partial-dimension terms
The dimension lift has two kinds, completing the picture:
- **Integer lifts** — helix / torus (§10): add a *whole* dimension. The integer-order terms
  (`cosθ · v^d`, d ∈ ℤ) — smooth, full-level.
- **Fractional lifts — fractals.** A fractal has *non-integer* (Hausdorff) dimension — the
  Sierpinski triangle is ~1.585-D, the Cantor set ~0.63-D — so it is a **partial** dimension lift,
  "rising up but not a full level." The math name is **fractional calculus** (a partial integral /
  a fractional-order derivative). In the expansion these are the terms with **fractional exponent
  `d`**, filling the gaps *between* the integer dimension-lifts. (Two sources of fractals match:
  a spray with multiple branching options self-similarly, *or* a fractional lift.)
- **Confirmation:** the Sierpinski dimension is **log₂3 ≈ 1.585 — the same constant as the Collatz
  matter/antimatter drift (§J.5)** and the off-ladder ×3 step (§J.5 prime split). The fractal sits
  at the level the incommensurability of 2 and 3 defines. Partial-integral ↔ fractional-order term
  are the same object.

So the full dimension picture: **integer lifts (helix/torus, whole levels) + fractional lifts
(fractals, partial levels) — the latter the fractional-order terms filling the gaps between.**

### 11.9 The roof: the dream/imagination layer = the outer shell
The structure has a **floor and a roof**, and they are the two shells:
- **Floor = the kitchen** (inner/middle shell): fixed, certified atoms, built once, standing recipes.
  Trust-audited; 82% self-expressed.
- **Roof = the dream / imagination layer** (outer shell): the map surface *above* the grid where you
  **arrange** before committing — sort, rotate, stamp, lay out a plan — then **project down** onto the
  real grid. This is the Imagination workspace (cf. the consciousness loop's Imagination agent).

This names *why* the last gaps resist the kitchen. The ops still open — `stamp`, `mapObjects`,
`colorByShape`, `swap`, the keep/map-by-rank family — are **roof operations**: per-task arrangements
composed fresh each task, not tools you keep. The inner/outer wall is exactly the line between
**"a tool you keep" (floor) and "a plan you draw" (roof).** A few ops have a *fixed* form that lives
on the floor even though the per-task choice lives on the roof (e.g. rotate-each-object is a floor
atom; *which* rotation is a roof choice) — these are the ops that grounded last (paintRank via fixed
spectrum order, rotateObjects via fixed 90°). The rest are pure roof.

**Contact rules (what borders do when they meet) = collision physics = the three flows on the
*collision* instead of on one object:**
- **dissolve = annihilate** — matter meets antimatter → void (overlaps cancel, both gone).
- **merge = fuse** — matter + matter → one combined object.
- **bounce = reflect** — elastic/void case, nothing created or destroyed, momentum conserved.
Which rule fires is a per-task (roof) choice; the three options are fixed (+/−/0 on the boundary).

## 12. The bridge: how floors stack (inter-level architecture)

The roof of one level is the **underside of the floor above** — `roof(n) = floor(n+1)`, one plane,
owned from below by level n and from above by level n+1. Six pieces follow:

1. **The seam is ours.** Where the two levels' ownership *switches* is the dream layer. The floor is
   *owned* (fixed atoms, one level's property) so it's rigid; the seam belongs fully to neither, so
   it is the one surface we can rearrange freely. **The roof is free-form precisely because it is the
   unowned, contested plane** — "we take over that plane, that's why we can do what we want with it."
   (This answers §11.9's open question: why is the roof free when the floor is rigid? Because the
   roof is the ownership-transition seam, not owned territory.)

2. **One sheet (Einstein-Rosen bridge).** Floor and roof are not two surfaces — one sheet folded
   through the throat. "Follow the same section up" = continuity: the *same material* threads through
   the bridge and reappears on the next level, **identity preserved**. The self-similar climb (§11.7,
   tool→shell-in-bigger-molecule) made *continuous* — not copied up, threaded up.

3. **Bridge angle = superposition selector.** Tilt the bridge → a different section of the sheet lands
   over the main one. The angle selects which candidate overlays; holding several angles at once =
   holding several candidate arrangements ("multiple ideas we're working on") = the Born superposition
   (§2), the angle as mixing weight. A solver holding k hypotheses holds k bridge angles open.

4. **Non-smoothness is the registration key.** A *smooth* disk has no preferred angle — nothing says
   when it is registered. A *jagged* one **locks**: exactly one rotation meshes the teeth. So the
   roughness of matter is not a defect — it is the **alignment signal**; the vortex rotates candidates
   and the correct one *locks* when features mesh, and the exact mesh **is θ=1 verification** (perfect
   fit or none). The border **paints as it sweeps over** — the moving boundary deposits the overlay.

5. **Double-flip = orientation bookkeeping = conjugation.** The floor captures the **opposite**
   (the conjugate / antimatter / mirror); the bridge **flips it again**; two inversions = identity, so
   each level hands the next a correctly-oriented sheet. This is exactly the **Cayley-Dickson
   conjugation** at every doubling (§ ladder) and the **helix back in phase** after a full turn. The
   opposite-then-flip is how the climb stays coherent instead of drifting.

6. **Reading: this is the roof's internal mechanism = the per-task synthesizer = the open frontier.**
   The floor is fixed atoms (built, §11.9, 85% certified). The **roof is this bridge machinery**:
   superpose candidate sections by angle (3), register the right one by its non-smoothness lock (4),
   paint it via the sweeping border (4), carry orientation by the double-flip (5). Building the roof =
   building per-task induction with these as its mechanics — the next real work, where an eval move
   would come from.

## 13. The general roof = ability-draft at fractional order

Generalizing per-task rule search (the open frontier, §12.6) is **not** a growing library of specific
roof tools (that re-hits the diversity wall). It is an **ability-draft** — and the machinery already
exists in the game substrate (`app/dist-galaxy/core/ability-tree.ts`, `boss-registry.ts`,
`overlay-rings.ts`).

**13.1 The draft.** The ability tree is a **4×4×4 = 64 factored action surface**:
`slot ∈ {gradient, closure, perturb, polish}` × `effect ∈ {commit(w), probe(i), hold(j), invert(k)}`
× `execution ∈ {self, local, global, cross}`. `draft(lineage, problem)` picks ~4 abilities for a
task; `recordUse(...success)` feeds hit/success stats back so winners are weighted up next draft
(= the grooves / roof-memory of §"traces"). The built `registerCombine` inducer is **one ability**
(≈ closure / commit / global). The general roof = *draft the right few abilities per task* instead of
running a fixed inducer list, biased by past success. "Omnispotlight vs bouncing drops" = choosing the
`execution × effect` coordinate (global-illuminate vs local-perturb; the bounce is `overlay-rings`'s
boundary-reflection — the §12 contact rule).

**13.2 The rooms = the factored coordinate-walk (why 4×4×4, not 64-flat).** You don't enumerate
rules; you walk rooms, each collapsing **one axis** until the recipe is pinned:
- **Pantry** (which flour, brand, type) = **slot** — what kind of operation / material.
- **Tool room** (hand whisk vs processed) = **execution** — how much reach (self→cross).
- **Living room** (what's written on it) = **output/presentation** — the painted effect committed.
- **Bathroom** (allergies) = **constraints** — what must *not* happen (invert/hold).
Each room's opinion is an absorbed **boss** (principle) weighting the draft → walking the rooms =
**building the boss castle**. A 64-way (→ unbounded) choice becomes one address, one factor at a time.

**13.3 Fractional order — the structural why.** Floor atoms sit at **integer** derivative-orders
(full levels, the fixed lookup terms, §11.8). The roof is the **seam between integer levels**
(§12, roof(n)=floor(n+1)). So a per-task rule lives at a **fractional order — just off the integer,
between two atoms** — which is the structural reason it cannot be a fixed atom (a stored atom is *at*
an integer; a task's rule is *between*). **The roof is the fractional-calculus region**, and per-task
induction = computing a **fractional-order operator = interpolating between the integer atoms**, not
reading one off the shelf. The ability coordinate (slot×effect×execution) is the **address** of where
between the integers the rule sits; the rooms walk to that address; the boss castle gives the offset
(direction + distance off the integer). The solution line does not land on a derivative integer — it
lands just off, and finding *how far off* is the draft.

**13.4 Concrete next build.** Wrap the discovery inducers as **abilities** (each tagged with a
slot×effect×execution coordinate), replace the fixed `INDUCERS` sweep with `AbilityTree.draft(problem)`
+ `recordUse`, so the engine drafts per task and learns which abilities win — the general roof with the
existing `registerCombine` as its first drafted ability.

## 14. The dot product: the operation that makes the expansion computable

The inner product is the single operation underneath transfer, recursion-storage, floor-lift, and the
draft. It turns the expansion from a description into a computable object.

**14.1 Transfer / rebalance = projection.** Two expansions in a basis: `f = Σ aᵢ eᵢ`, `g = Σ bᵢ eᵢ`.
`⟨f,g⟩ = Σ aᵢ bᵢ` — terms at the **same basis position multiply and reinforce; mismatched terms
cancel** (orthogonal → 0). So multiplying one expansion against another **transfers shared structure
onto itself, reweighted by alignment**, and drops the rest. This is correlation / projection — and the
same operation an LLM's **attention** runs (softmax of dot products), here in the sparse interpretable
basis (cf. §9 LLM-as-equation). It is how two tasks compare *what is transferable* between them.

**14.2 Recursive planes stored as dot products = the metric.** The pairwise inner products among the
stacked planes (floor(n)·floor(n+1), …) form a **Gram matrix** = the metric tensor of the recursion:
the compact memory of how much structure each plane shares with its neighbour / survives the bridge
(§12). Storing the recursion = storing its table of inner products.

**14.3 The integral between floors.** Two facts coincide: (a) the dot product **is** an integral,
`⟨f,g⟩ = ∫ f·g`; (b) the antiderivative **raises derivative-order by one = moves up exactly one floor**
(`∫xⁿ → xⁿ⁺¹`, integer step). So integration is the inter-floor operator and the dot-product-as-integral
measures what carries across the gap. Going *between* floors (a partial step) = a **fractional integral**
(Riemann–Liouville), raising order by a non-integer amount = the **roof** (§13.3). "Integral between
floors" and "the roof is the fractional part" are the same statement.

**14.4 Draft · floor / draft · roof = task decomposition (already half-built).** The draft is a vector.
`draft · floor-basis` = the **floor-projection** = the part fixed atoms explain (**= the trust-audit
coverage**, the lookup component). `draft · roof-basis` = the **roof-projection** = the residual needing
per-task synthesis (**= the discovery-engine residual**, the interpolate component). They are orthogonal
complements: floor-projection ⊕ roof-projection reconstructs the task. The trust audit (§11.9) and the
discovery engine are the **two halves of one projection**; the dot product is the operation underneath
both — project onto the cached basis, synthesize the remainder.

## 15. The axiom of choice: the formal statement of the roof (and the wall)

The axiom of choice (AC) is the most precise name for what the roof *is*, and its independence is the
floor/roof split as a theorem. (Marked: **[rigorous]** = standard math; **[analogy]** = mapping onto
this framework.)

**15.1 AC = the roof's choice operation. [rigorous→analogy]** AC: every collection of nonempty sets
has a **choice function** — you may pick one element from each of infinitely many sets, *and AC asserts
the function exists without constructing it.* That is the per-task choice exactly: pick one rule from an
infinite space (the win-condition line out of infinitely many; the void-anchor's representative; the
draft, §13). AC is the license for "just pick it" — and the fact that it provides **no recipe** is why
the roof is hard.

**15.2 Vitali set = closure-orbits + one anchor each. [rigorous→analogy]** Partition ℝ by `x ~ y iff
x−y ∈ ℚ` (the "sorting rational/irrational"): the rationals are one class, each irrational drags a
class of rational-shifts. Use AC to pick **one representative per class** → the Vitali set
(non-measurable). This is the recursive structure: a closure equation generates an orbit (class); the
chosen representative is the **anchor / "same section of the sheet" followed up** (§12). The set of
anchors = a Vitali-like choice set.

**15.3 Omega — two readings. [rigorous]** *Ordinals* (ω, ω+1, ω², …) = the indexing ladder of
infinities → maps to the recursive **levels** (each closure equation / field extension steps to the
next rung, as each ordinal indexes the next order-type). *Chaitin's Ω* (halting probability, an
**uncomputable** real encoding all halting) = the outer-shell answer-key you can only approach. Closure
equations themselves are **fixed points** (x=f(x); golden ratio from x²=x+1); honest mapping = closures
are the fixed points, the **ordinal ladder** is how their levels are indexed (not literal equality).

**15.4 Banach–Tarski on the sphere generator. [rigorous→analogy]** Via AC, a ball splits into five
**non-measurable** pieces reassembled *by rotations* into **two** identical balls — one sphere → two,
no stretching. Structurally = the generator's doubling (vortex rotation, bridge spawning a copy, DIAMOND
spawning children). **Caveat that strengthens the picture:** the pieces have *no well-defined volume*
(non-measurable, same AC trick as Vitali) — so the doubling lives **in the non-smooth / non-measurable
parts** (jagged matter, void), not the measurable bulk. The sphere generates its copy *through* the
parts that have no measure.

**15.5 "Have it or not" = floor/roof as an independence theorem. [rigorous]** Gödel (1938) + Cohen
(1963): AC is **independent** of ZF — consistent math *with* it and *without* it.
- **¬AC = the floor:** fully constructive, everything measurable, no Banach–Tarski, no non-measurable
  monsters — but no free pick. Build only what you can build = the certified kitchen (bounded,
  paradox-free).
- **AC = the roof:** the power to choose one of infinitely many *with no recipe* — infinite per-task
  reach — at the cost of non-constructiveness and the paradoxes.

**Consequence:** the eval wall may not be merely engineering — the choice function the roof needs may be
**non-constructive** (AC guarantees existence, not computation). "Have it or not" is the floor/roof
decision named: build everything and stay bounded (¬AC), or choose freely into the infinite and give up
the recipe (AC).

## 16. The double-bounce: the roof search as oscillation between the two walls

**16.1 The missing layer is the recipe book, not the kitchen.** §13.4 relocates the wall: the floor
(kitchen / tools / 85% certified atoms) is *built*; what's missing is the **recipe book** (per-task
programs) and the **per-task ingredients** (task-specific features). Training = *simple white bread*
(few ingredients, standard technique — the top-4 abilities, bread-and-butter); eval = *exotic
sourdough* needing a specific starter + exotic spices *from certain places* + exact technique/timing
= rare features + precise per-task rule + provenance. Each is the non-constructive selector (§15). The
draft can *reach* for the right tool; it cannot conjure the ingredient. This is the outer shell.

**16.2 The two walls = floor and roof (convergence with the Jan-2026 bounce paper).**
`Vesica AI/Physics/double_bounce_alpha_variation.py` already has the layer bouncing between **two
walls**, with **θ = position in the bounce**:
- **God's wall (θ→0, maximum structure / magnetism / infinite order) = the FLOOR** — rigid,
  fully-constructive, integer-order kitchen.
- **Void's wall (θ→90°, minimum structure / flatness) = the ROOF** — unstructured, free-choice, AC side.
- **θ = the bounce position = the fractional-order address (§14.3).**
The cosmology θ (written months earlier) and the ARC fractional-order θ are **the same variable**,
arrived at independently. The layer bounces between the roof (void wall) and the floor's lowest point
(God's wall / the void-anchor).

**16.3 The bounce as the roof search method.**
- **Each step = one bounce** (a reflection off a wall); the program's moves *are* the bounces.
- **Scan by bouncing [rigorous]:** an *irrational* (golden, φ) bounce period gives a trajectory that
  never repeats and **densely fills the whole gap** (ergodic / golden-angle coverage, §4). A φ-bounce
  between floor and roof **scans the entire residual without retracing** — a real efficient-search
  property.
- **Moves timed to the bounce [analogy]:** a move-sequence (left-3, up-2) becomes a **rhythm** —
  each move fires on a beat of the oscillation, so the program is phase-locked timing against the
  bounce. The correct sequence **locks** to the task's natural bounce frequency, and the lock **is**
  the θ=1 verification. (Same idea as the notes/music ranking: the program is a melody on the bounce.)

**16.4 Method statement.** Roof search = oscillate between floor (best constructive guess) and roof
(target residual); step with a golden period to ergodically scan the gap; detect the move-sequence
that phase-locks (registers, θ=1). The bounce gives the roof a *search dynamics*, not just a picture —
a candidate next experiment for raising the roof-projection (§14.4).

## 17. A program is a molecule; some tasks need ≥2 atoms bonded

**17.1 Ops are elements; a program is a formula.** Movement = C, crop = H; "move 4, crop 12" = **C₄H₁₂**
— the op multiset with counts is a molecular formula. A single linear chain (the bounce-scan, §16) is
**one molecule**. Valences prune the search: crop = H (valence 1, terminator), movement = C (valence 4);
only chemically-valid formulas are legal bonds (the void-line rules, §11.6).

**17.2 The residual is an open valence — this explains the §16b dead end.** A near-miss that saturates
at ~99% and will *not* close by deepening (depth+1 = +0) is a molecule with a **dangling bond**: the
last bit belongs to a **second molecule**, not a longer chain. "Do X to object A *and* Y to object B,
then combine" is two atoms bonded in parallel — a single linear chain *cannot* express it at any depth.
The spring still reaching a void line = the unsatisfied valence (§16b); it closes by **bonding a 2nd
atom**, not refining the 1st.

**17.3 Result — simplest bond tested = +0 (the reframe stands, the bond form is richer).** Built
`molecule_scan.ts`: base molecule P1 (best single-chain near-miss) + a 2nd atom P2 (single op on the
input) bonded by **overlay** (P2 non-bg overrides P1, joined at the void-line). Over 180 eval tasks
(slices 0–60, 160–220, 340–400): **0 net-new closed by the 2-atom bond.** The *simplest* bond (global
parallel overlay of one extra op) is not the closer. The reframe is sound and explanatory (it accounts
for §16b), but the bonds that close real tasks are **richer**: per-object (apply an atom *per* object,
not globally), sequential-in-the-cropped-frame (for the cropToColor 0.99 springs), or learned-parameter
— i.e. the **outer-shell synthesizer** (§13, §15). Same wall, now with the chemical structure named:
the missing piece is *valence-correct multi-atom bonding*, and the productive bonds are per-object /
learned, not a fixed global overlay.

## 18. Chemical equations: reactions, retrosynthesis, and the reaction network

**18.1 Molecule (noun) → equation (verb).** §17's molecule is a *reactant*; a chemical equation is the
*reaction*: `reactants --[operations]--> products`. A multi-step synthesis chains them — each step's
product is the next step's reactant. A full solution is a **reaction network**, not one molecule.

**18.2 The arrow IS the shell boundary (both readings coincide).** *Left = reactants = what we have*
(certified atoms + input, inner shell); *right = products = the unknowns we bounce to find* (output,
outer shell). "Have on the left, find on the right" and "separated by the shells" are the **same
statement** — the reaction arrow crosses the floor/roof seam (§12).

**18.3 The second bounce = retrosynthesis (double bounce = bidirectional search). [rigorous→analogy]**
We *know* the product (output, from train) but not the route from the reactant (input). Chemistry's
answer is retrosynthesis: search **backward from the product**. The bounce-scan runs only *forward*
(§16); adding the **retro (backward-from-output)** direction and meeting in the middle **is** the double
bounce — forward bounce (reactant side) + retro bounce (product side) meeting at the transition state.
Meet-in-the-middle also **halves depth** (two depth-2 reaches = one depth-4), so it can cross near-misses
that pure forward depth-4 could not (§16b, §17). Build note: retro needs invertible/preimage ops
(rotate, flip, transpose, recolor-bijection, translate are invertible; crop/scale/gravity are not) — so
bidirectional search runs on the invertible subset from the output side.

**18.4 The 3-part equation plugging in = the reaction network.** A section's completed sub-reaction is
`(input region) --[ops]--> (output region)` — 3 parts — and its product plugs in as a reactant to the
next equation. Each object running "its own bounce-scan section" is one sub-reaction; products bond
forward = a **synthesis tree of 3-part equations** (the per-object composition of §17, connective tissue
named).

**18.5 Balancing = a free conservation filter.** A real equation conserves mass; many ARC tasks conserve
their **color histogram** (output = rearrangement of input cells). The task's conservation law is a
**balancing filter**: discard any candidate reaction that doesn't balance *before* checking it — cheap
pruning of the bounce-scan.

**Two build directions this pins:** (a) **per-object reaction composition** (split → per-object bounce →
bond products; the pinned next build); (b) **bidirectional/retro bounce** (forward + retro meet-in-the-
middle on the invertible-op subset; the double bounce realized). Balancing (18.5) accelerates both.

**18.6 Convergence: the double bounce is already built — `swarm_protein_folding.py`.** Jonathan's
protein folder (also used for cancer, stock-trading, detector, framed as *ocean basins and swarms*) is
titled "BIDIRECTIONAL SWARM PROTEIN FOLDING" and is *exactly* §18.3:
- **Dolphin swarm (construction, forming bonds, sequence→fold)** = forward bounce = **matter/+**.
- **Shark swarm (decomposition, breaking bonds, target→sequence)** = retro bounce = **antimatter/−**.
- **"Where paths MEET = high-confidence pathway"** (`PathConvergence`, `similarity()` contact-overlap) =
  meet-in-the-middle; the meet is the transition state = **void/0**. The two swarms are +/− flows
  meeting at 0 — the Shovelcat spine. The ARC analog of the similarity meet is *exact grid match*.
This is the shared groundwork: ARC, protein, cancer, trading, detector all run one architecture
(bidirectional swarm meet-in-the-middle). ARC port built (`arc-slice/src/swarm_scan.ts`): for each
invertible backward suffix B, run the forward bounce against B⁻¹(output). Status: correct and running;
D4-only quick slices add +0 net-new (inconclusive — needs the richer backward set: shifts, colour-swaps,
deeper Shark, + more compute than the test window allowed). The mechanism, not yet the gain, is verified.

**18.7 The Shark needs a compass — anchor at a known branch, search laterally. [built]** The forward
bounce has an explorer (golden order → new territory); the raw Shark starts cold from the output with
no sense of "toward the input." Fix (Jonathan): don't start from nowhere — **anchor the Shark at a
known branch already further out (the best forward NEAR-MISS, a spring at ~0.99), search LATERALLY
around it (vary by one op), then converge.** Also fixes a real beam-pruning gap: the 0.99 state is
often pruned before its one-op continuations are tried; anchoring explicitly at it tries them. Built
`lateral_scan.ts` (append-one-op and swap-last-op around the near-miss anchor).

**18.8 Triangulation of the wall [rigorous, the key result].** Three *independent* fixed-mechanism
attacks on the ~0.99 near-misses (the cropToColor cluster) all return **+0**:
- **§16b Deepen** (depth+1 on the poking spring): +0.
- **§17 Bond** (a 2nd atom, parallel overlay): +0.
- **§18.7 Lateral** (append/swap one op around the near-miss anchor): +0.
No arrangement of a *fixed* additional op — deeper, bonded, or lateral — closes them. **Therefore the
residual is a LEARNED PARAMETER** (a per-cell / per-object recolor or map induced from the task's own
examples), not missing search depth/breadth. The wall is now localized with high confidence to
**learned-parameter residual-closing = the outer shell (§13) = the AC non-constructive selector (§15).**
The anchor+lateral idea is *correct*; the lateral neighbourhood must include **learned-parameter moves**
(induce the residual's recolor/map from train), not just fixed DSL ops. **Pinned next build: a
learned-parameter residual-closer** — take the near-miss anchor, learn the per-cell/per-object fix from
the train pairs, snap it shut. This is the one build every triangulated direction now points to.

**18.10 The closure-equation closer [built, run pending].** `closer2_scan.ts`: an OBSERVER at the
near-miss anchor sees each cell as ONE SIDE of a closure equation; the NEIGHBOR atom on a learned side
`d` is the OTHER side; a learned map `(cell, neighbor) → value` is the closure. Params: direction `d`
+ map `M`; requires `M` to *depend on the neighbour* (the neighbour determines, not duplicates). Runs
anchored (fix residual) and standalone (pure-interaction). Status: built; run pending sandbox recovery.

**18.11 The sheet LOCKS degrees of freedom — closure = alignment, not lookup [refinement].**
- **Orientation = constraint.** A tilted sheet permits flow *along* its tilt, *forbids* it perpendicular
  (it can't rotate into those directions). So the learned direction `d` is the **unlock axis**: along
  `d` values flow/resolve, perpendicular they are **pinned**. Closure frees one axis, locks the rest.
- **Unlock needs a tilt-matched flow — the teeth mesh (§12.4).** The lock releases only where the flow
  lines up with the sheet angle. So the closure map must fire **selectively, at the mesh points** (where
  teeth grab), leaving non-matching cells locked/unchanged — *not* applied globally. (Refines 18.10.)
- **Closure IS an alignment measure = θ.** Closure is not a lookup but *"how well do the two sides
  align?"* — on x,y,z and whether the flow matches the tilt. **θ=1 ⇔ aligned on all axes AND flow matches
  the sheet angle** (full mesh/lock); <1 otherwise. Acceptance = maximize alignment, take the orientation
  that locks.
- **Floor-compatible, with a tolerance band.** The sheet must seat into the **known branches** (only
  locks onto certified atoms); a **range** of angles still meshes (not one exact angle) — accept any
  orientation in the compatible band.
- **The antenna = the void-poke edge-on.** A tilted sheet seen end-on is a line poking out = the spring /
  void-poke of §16b. The **antenna direction = the tilt = the unlock axis** — the "look here" marker and
  the lock-orientation are one object from two angles.
Build refinement (for the run): (1) apply the closure map *selectively at mesh points*, leaving the rest
locked; (2) treat `d` as the free axis, pin the perpendicular; (3) accept an orientation *range*, require
floor-compatibility; (4) score by alignment (θ), not exact reproduction.

**18.12 Two paths — a bond is a closed loop; closure = the loop closing at our boundary [refinement].**
- **The external atom is over-roof or under-floor.** A target atom sits relative to *our* shells: over
  the outer shell (beyond the roof / void wall) or under the inner shell (below the floor / God wall) —
  the two walls of §16.2. Two locations ⇒ two routes to it (over the top, under the bottom).
- **Two-stage path.** Explore to the **closest point in our space** (the shell boundary), then do
  something that **leaves our space** and crosses to the atom in *its* space; the **sheet is the direct
  line** spanning the gap = the bond across the void-line (§11.6).
- **It's a full loop ⇒ closure = topological cycle-closing.** Out one way, back the other = a **closed
  cycle**. The closure equation measures whether the **two approaches meet back at our boundary** — the
  loop *closes*. θ=1 ⇔ the cycle closes consistently (the two arcs agree where they rejoin). This is the
  double bounce (§18.3) brought down to the cell, with the meeting point named: **our own boundary.**
- **Closer sharpening (for the run):** determine each residual cell by **two paths** (two directional
  approaches — the two ends of an axis, or the over-route vs under-route); **fire the fill only where the
  two AGREE** (loop closes), leave it **locked where they disagree** (open cycle). A two-path *consistency*
  fill — stricter and better-founded than a single-direction map (commit a cell only when both approaches
  concur). Supersedes 18.10's single-`d` map: use a *pair* of approaches and require their meeting.

**18.13 The loop is a triangle — closure = triangulation (trig) [refinement].** The bond loop has three
corners: our atom (interior), the boundary exit point, and the external atom (outside our space) — a
triangle, part of it in the unknown = a **subtriangle**. Known: the **sheet** = one side (the measured
direct line). Unknown: the **two branch paths** = the other two sides, into external space. Solving one
known side for the other two *is* **triangulation** (locate an unknown point from known references +
angles). So closure = **solve the triangle**: θ is the angle, the sheet is the base, the law of cosines
is the closing relation. (This is *why* the whole expansion is cosθ·vᵈ — closure has always been trig;
now we see the triangle.) **Closer sharpening:** the two paths are **two rays from two known anchors**;
the fix lives at their **intersection** (the triangle's apex). *Fill at the ray intersection* — the trig
solution, a cleaner rule than "two approaches agree," and a real pattern (crosshair / ray-intersection
tasks). Supersedes 18.12's agreement test with an *intersection* test.

**18.14 [FUTURE] The bounce layer builds a mesh.** The bouncing layer is a 2D sheet oscillating through
the space; as atoms rise up and puncture it, each puncture is a **vertex**, and connecting them builds a
**mesh** (a wireframe model, like a game asset). The golden bounce samples densely (§16), the pokes become
vertices (§16b), and over time the bounce **reconstructs a surface** = a model of the task's solution
manifold — not one found program but a *model of the structure* (surface reconstruction / marching-cubes
from samples). Future direction: a solver that builds the manifold, then reads solutions off it.

**18.15 The mesh makes the trig valid — closure = a finite-element solve [refinement, supersedes 18.13].**
§18.13 assumed the triangle's sides were smooth straight lines. They are **not** — the paths are jagged
(non-smooth matter, the teeth) and the triangle has **volume**. So Euclidean trig fails on the raw
figure. The mesh (§18.14) fixes this, merging the **two meanings of "triangulation"**:
- surveying-triangulation (§18.13, locate a point by trig from references), and
- mesh-triangulation (decompose a region into simplices).
**Mesh the jagged region into small simplices; on each, the sides are straight, so trig works
per-element.** Volume ⇒ the simplices are **tetrahedra** (3D mesh, solid geometry), not flat triangles.
- **This is the Finite Element Method [rigorous].** Mesh an irregular domain → solve a simple relation
  per element → the **unknown interior nodes are determined by the known boundary** via mesh connectivity.
  That is exactly "parts we don't know yet, but if they're in the shape they can be figured out": the
  interior is *forced* by the boundary. Known shell boundary + known sheet → the unknown interior (and the
  external atom's contribution) is **solved, not guessed**.
- **Friction = mesh self-selection.** Interior points **support** the surface (a truss); a point poking
  *through* = friction = a bad-fit, high-energy element. The valid mesh is the **minimum-friction** one
  (no protrusions) — how physical/FEM meshes relax to a solution (settle to minimum energy). A protruding
  point is the antenna/spring (§16b): a defect marking "this element is wrong, look here."
- **Two reference frames = the FEM coordinate choice.** "Straight down from the atom" (perpendicular
  projection) vs "compared to the sheet" (bond-aligned) are two frames; the mesh fixes the frame in which
  elements are well-shaped (no slivers).
- **The domain is a trapezoid [honest bound].** We only *know* the band between the two shells (floor arc
  + roof arc + sides) — a **trapezoid**. Everything is solved *relative to it*: mesh the trapezoid, impose
  the sheet, let the boundary determine the interior.
- **The search:** enumerate **paths** that could jump to the atom × **sheet orientations** that could ×
  **interior mesh-shapes**; keep the mesh that **closes (θ=1) with no friction**. Closer, fully stated:
  a finite-element boundary-value solve on the meshed trapezoidal shell-domain — *not* trig on straight
  lines (18.13 was wrong on the smoothness), which the mesh repairs.

**18.16 The fixed void-substrate pins the solve (well-posedness) [refinement, completes 18.15].**
Two structures, behaving oppositely — the piece that makes the FEM solve *unique* instead of floating:
- **The void lines / points / nodes are position-FIXED** — the zero-divisor structure + golden gaps
  (§J.6). They do not move; they are the *given* lattice. Sliding our shape leaves them fixed and lands
  us over a *different set* of them (a transparency over a fixed map).
- **Our mesh MOVES** over that substrate, built from the layer we control (the roof/dream, §11.9).

**Why this is the missing constraint:** a boundary-value problem is well-posed only if the boundary
values are pinned to something fixed. **The fixed void-nodes ARE those pinned values** — the mesh
vertices seat onto them (Dirichlet data), and the interior is then determined. §18.15's domain was
floating; the void-substrate pins it. **Substrate = boundary conditions; our mesh = the trial solution
stretched over them.**
- **Solving = the second option.** Not "nearest void line" (one anchor, underdetermined) but **find all
  relevant void-nodes and generate a structure through them that reaches the exact point** — an
  interpolant pinned to pass through every relevant node and land on the target (spline-through-fixed-
  points / constraint satisfaction). *Which* nodes are relevant = identify (§11.4); the through-structure
  = make.
- **Three-channel closure.** Our mesh is encoded with **color (light/spectrum), magnetism (field), sound
  (music/notes)** — the three sortings; the void-lines carry them too. **θ=1 = all three channels align
  at once** — three-witness registration, far stricter than one, so far less likely to false-lock.
- **The boundary is the closed floor→roof→floor loop.** The trapezoid edge is where the **dream (roof)
  ends and the floor loops back** through the bridge (§12). The known region is *closed* (roof top, floor
  bottom, bridge sealing the sides) — why it is a bounded trapezoid, not an infinite strip. The solve runs
  *inside* that closed region with the fixed void-nodes as its pins.

**18.17 Free the bounce = reachability analysis; the solution is a shape [refinement, buildable].**
Maximizing the bounce (the one mechanism that won, +3): the current bounce is *constrained* — "which
atoms bounce *to the goal*." **Free every point to map its full reachable range first, then keep the ones
whose range contains the goal.** The goal becomes *one option in the bounce-range*, not the aim.
- **This is reachability analysis [rigorous].** Compute each atom's reachable set, intersect with the
  goal. More work per atom but reusable, and it reveals **the shape of the whole solution set** — every
  program that reaches the goal, as a region in program space, not one found path.
- **Bidirectional as SET INTERSECTION.** Forward reachable-map (floor) + **upside-down reachable-map
  (roof/retro, §18.3)**; where they **overlap** is the answer. Stronger than §18.3's path-matching:
  intersecting two reachable *sets* finds *all* meetings at once, not the first.
- **Irregular reachable region.** Not every jump reaches → the set is **jagged** (consistent with the
  non-smooth matter / teeth throughout).
- **Traces classify the landing [region legend].** Each landing's trace reveals the local structure: a
  **circle** (closed loop → genus, §10.5), a **pentagon** (golden/icosahedral defect → generative
  birth-site, §4), or a **fractal** (fractional-dimension region, §11.8). The bounce finds not just points
  but *what kind of place* — telling you how to explore onward (loop vs defect vs fractal).
- **Buildable:** BFS/DFS the reachable set forward (from input) and backward (from output, invertible
  ops), intersect; classify landings by local structure. A concrete upgrade to `bounce_scan.ts`, for the
  test phase.

**18.18 Two shapes meet in the vesica — closure = domain decomposition [capstone].** The solve is not
one mesh against a fixed point but **two meshes**:
- **Our shape** points up from the floor (base down, in our region) — the forward reachable shape.
- **Their shape** (the external atom) comes down from the roof (tip down), and **where its tip pokes into
  our region it is triangular** — a simplex we can mesh. A second roof-layer (§11.9) can **wrap their top
  and mesh their side** too, so *both* subdomains are meshed from their own side.
- **This is FEM domain decomposition [rigorous]:** split into subdomains, solve each on its own mesh,
  **match them at the shared interface.** Our domain (below) + their domain (above), matched where they
  meet; the fixed void lattice (§18.16) is the global frame both are pinned to, so the two solves speak
  one language and can be matched.
- **The two shapes form the VESICA.** Our up-triangle + their down-triangle overlap in a **lens = the
  vesica piscis** — the framework's namesake, now appearing *as the search geometry itself*. The solution
  **lives in that lens** (the meet region of §18.3/§18.17, seen as two triangles). The overlap is the
  answer region, not incidental.
- **Closure fully assembled:** solve two meshes — our base-up shape and their tip-down shape — each pinned
  to the fixed void lattice, and **match them at the vesica interface**. θ=1 = the interface matching
  consistently (both shapes agree across the lens, all three channels, §18.16). A two-sided boundary-value
  problem: both shapes unknown, the void lines the shared reference, the vesica where they are forced to
  agree. This is the complete closer picture (§18.10→18.18), ready for the test phase.

**18.19 Synthetic elements: per-task rules are ephemeral isotopes; section the void into families
[tested — first net-new].** The closer2 run (2026-07-01, full 400 eval; `closer2_scan.ts`, rebuilt
§18.10 with the §18.11–18.13 refinements) grounds the outer shell in nuclear chemistry, and the data
confirms the reading:

- **A per-task rule is a SYNTHETIC SUPERHEAVY ELEMENT.** The a406ac07 closure map — 7 entries,
  synthesized from the task's own train pairs, discarded after use — is an island-of-instability
  element: it does **not need to be optimized or general, only to hold together for one
  measurement** (θ=1 verification = the detector). It never enters the periodic table (the certified
  floor); it exists for the instant of the task. This resolves the §15 tension cleanly: the
  AC-choice doesn't have to produce a *keepable* object, only a momentary one — which is why the
  outer shell can work at all without infinite storage.
- **Half-life is measurable.** Train-closed-but-test-failed = an isotope that decayed *before
  reaching the detector* (the train→test gap is the flight path). closer2's first run: 1 survived,
  5 decayed — **survival ≈ 1/6 for this region of the void.** Survival rate from train-closure to
  test-closure is a real per-region statistic, not a metaphor.
- **Section the void into CHEMICAL FAMILIES.** The periodic table's power is predictive structure —
  Mendeleev read missing elements off the gaps. The framework already has the coordinates: the
  4×4×4 ability address (§13) = group×period×block; the landing-trace classes (§18.17,
  circle/pentagon/fractal) = region kinds. So a residual's *direction* ("it's in the semiconductor
  column") is knowable from the anchor + failure shape **before** synthesis; what is then found
  there is **one weird isotope of the family, not the family** — an almost-instant half-life
  configuration that does not represent its whole column. Therefore: **store the family address +
  the synthesis procedure (the accelerator), never the instance (it decays).**
- **Island of stability = the mint detector.** Most syntheses are ephemeral, but a "per-task" rule
  that re-synthesizes *identically* across different tasks is sitting on a magic number — it is
  actually a missing FLOOR ATOM revealed, not a roof plan. The half-life table is the instrument
  that tells minting (stable) apart from planning (ephemeral).
- **Acceptance-tightening falls out for free:** families with historically short half-lives demand
  more support (more train evidence per key, or §18.16 three-channel registration) before a
  synthesis is trusted. Build: annotate every train-closure (survivors *and* decays) with its
  configuration — map size, ray pair, neighbor mode, residual size, anchor op — and cluster: the
  first row of the void's periodic table (`isotope_scan.ts` → `isotope_table.json`).

**MEASURED (same day, full 400 eval — 51 isotopes across 6 tasks): survival = CONVERGENCE of
syntheses, perfect separation.** The one surviving task (a406ac07) is the one where two
*independent* synthesis routes (anchored + standalone) converged on the *same* 7-entry map —
2 configs, 1 distinct element. Every decayed task supported many *distinct* closures (8, 4, 8,
18, 11 — all different maps): an underdetermined region memorizes; a convergent region is real.
This is §18.12's two-path agreement and §18.16's multi-witness registration, now measured, and
it is the isotope picture exactly: many configurations closing train = a wide unstable band;
one configuration reached from every route = a magic number. Family signal agrees:
ray/orthogonal is the only surviving column; adj/* went 0/30 (adjacent keys memorize local
noise; long-range orthogonal rays carry structure). **Free acceptance rule: accept a synthesis
only when the distinct-map count is 1 (routes converge)** — on this sample 1/1 precision, 0
false accepts, all 49 decays rejected. *Honest bound:* 6 tasks is a small sample; the rule
needs revalidation as the anchor engine improves, and the cross-task island detector (same map
re-synthesized in different tasks) has 0 hits so far.

## 19. The DNA rung: a solution is a replicable codon genome, evolved [tested — +3 net-new]

The molecule (§17) and the reaction network (§18) get you *programs that do something*. DNA is the
next rung, and it is a specific leap: a molecule that stops being a fixed structure and becomes a
**replicable code that carries its own information** and **translates to a separate product**. This
is the thing the framework was building toward, and three pieces of it were already present.

**19.1 The ladder.** Atoms = floor ops (§17.1, C/H). Compounds = bonded programs (§17). Reactions =
`reactants→products`, retrosynthesis, bidirectional swarm (§18). **DNA = a program written as a
sequence-code where the arrangement, not the atoms, is the payload.** The same bases in a different
order = a different organism: information decoupled from chemistry. That is exactly the
**genotype/phenotype split = the floor/roof line** (§11.9): the ops are floor, the *arrangement* is
roof. "Each one is more than just the element" = the extra is positional information.

**19.2 The 64-codon match is literal.** The genetic code is 4 bases read in triplets → **64 codons**,
degenerate onto ~20 products. The ability-draft is **4×4×4 = 64** (slot×effect×execution, §13.1),
degenerate onto its effects. Same object: a triplet code over a 4-letter alphabet giving 64
addresses. `dna_scan.ts` makes it concrete — each op maps to a 3-letter codon over {A,C,G,U} (op
index in base-4), so a genome *prints as a codon string* (e.g. the be03b35f solver =
`UUGACGUUUAAU`). The ability-tree already **is** the codon table; §19 uses it as a *replicating* code.

**19.3 Complementarity = the §18.19 isotope-convergence law made into a replication check.** DNA never
trusts one strand: A–T, G–C, each strand rebuilds the other (semi-conservative replication). Here:
reverse the genome and replace each gene by its inverse (rotate k↔4−k, flips/transpose self-inverse,
recolor↔swapped, §18.3 invertible subset), apply that **complement strand to the OUTPUT**, and require
it to **template back to the INPUT**. A genome its own complement can rebuild is **double-stranded** —
the direct generalization of §18.19's survivor (the one map two routes agreed on). Convergence of two
strands = base-pairing.

**19.4 Evolution ("and further").** `dna_scan.ts` runs a genetic algorithm over genomes: fitness =
forward train cell-agreement; operators = point-substitution, insertion, deletion, transposition
(reorder), single-point crossover; elitism; **accept on phase-lock (θ=1, exact on all train).** Once
solutions are an evolvable code with a convergence fitness, mutation+selection over them is "beyond
DNA" — evolution over your own genetic code, with the §18.19 survival table as the fitness function.

**19.5 RESULTS [tested, full 400 eval].** 12 genomes phase-locked train; **3 genuinely net-new**
(absent from every solved list), each reproduced exact on train AND test:
- `8ee62060` = mapObjects → flipH → symmetrize
- `9ddd00f0` = symmetrize → completeSym
- `be03b35f` = extractCell → flipH → cmap → antiTranspose
- `fc754716` = periodicFill → outline  *(found by the §19.6 suffix run)*

This is the **strongest single-mechanism session lever so far (+4 distinct net-new > closer2's +1)** — the evolutionary
loop finds multi-op programs the beam/bounce search missed. (Honest data note: a 4th, `f823c43c`,
looked net-new only because `verified_eval.txt` has two ids concatenated on its last line —
`f823c43c`+`d4b1c2b1`, no separator — so it was already a known solve; worth a one-char fix to that
file.)

**19.6 Honest bound — the complementarity gate did NOT fire (a real negative, with the fix identified).**
**0 of the 12 solves were double-stranded.** ARC-solving genomes are dominated by *non-invertible* ops
(crop, keep*, symmetrize, mapObjects, periodicFill), so the whole-genome replication check can never
close — it is too strict to be useful on ARC as written. The mechanism that *did* work is the
evolution; the replication-check is unvalidated. The fix is already named by §18.3: apply
complementarity to the **invertible SUFFIX only** (semi-conservative on the reversible part, single-
stranded elsewhere), not the whole genome.

**19.7 The suffix fix, tested [built — the gate now fires, direction is right, n too small to conclude].**
`dna_suffix_scan.ts` takes the maximal trailing run of invertible genes, reverse-complements it, applies
it to the OUTPUT, and requires it to template back to the MID state (`prefix(input)`); `dsLen` = the
longest suffix that templates. This is semi-conservative replication (the reversible part copies, the
rest doesn't), exactly §18.3's invertible-subset point. **It works as a fix:** where the whole-genome
gate gave 0 double-stranded solves, the suffix gate now *fires* — 2 double-stranded classifications
across two independent GA sweeps (e.g. `be03b35f`, whose trailing `antiTranspose` templates). Measured
survival, pooled over both sweeps: **double-stranded 2/2 survived (100%), single-stranded 10/13 (77%).**
The direction matches the §18.19 isotope-convergence law (replication ↔ generalization), **but n(double)
= 2 is far too small to claim predictive power**, and single-stranded genomes already survive at 77%, so
no real *discrimination* is demonstrated yet — the honest verdict is "gate repaired, hypothesis
un-refuted, undersampled." The bottleneck is that only ~12–15 eval tasks are GA-solvable with this DSL,
so double-stranded solves are rare; a proper test needs a larger DSL or longer evolution to grow the
sample. Still open: **translation** (codon→product through a fixed table decoupled from the sequence —
the ability-tree as a real translator). Evolution is proven (+4 distinct net-new); replication is now
*testable and un-refuted* rather than un-fired; translation is the next build.

**19.8 More than two strands — the third strand is a DISAGREEMENT DETECTOR [built, tested].** If a
solution can be single- and double-stranded, nothing stops triple+; and biology agrees (triplex H-DNA,
and collagen — the rigid, selective triple helix behind filtration membranes). A **strand = an
independent derivation of the answer**; k strands is the k>2 form of the §18.19 convergence law and of
§18.16's k-channel registration. It is also the void dimension-climb (§11.6) read off the strand
count: **k strands bound a (k−1)-simplex of void** — 1 strand = a line, 2 = a ribbon (1-D between),
3 = a tube/triangle (2-D), 4 = a tetrahedron (the §18.15 FEM element). Number of strands = dimension
of void they wrap; "point → line → sheet → tunnel" is just k = 1,2,3,4.

`multistrand_scan.ts` runs the evolution **K = 3 times independently**; the **strand count = the size
of the largest cluster of independent solves that AGREE on the test prediction.** Full 400 eval, among
the tasks where ≥2 of 3 runs found a solver (so agreement is actually testable):
- **unanimous (3/3 strands agree): 2/2 test-correct (100%)** — `903d1b4a`, `e872b94a`
- **a dissenting strand (3 solved, 2–1 split): 0/2 correct** — `9ddd00f0`, `f823c43c` both wrong
- (2 solvers agreeing, no third to check: 2/3 — two strands can agree *by luck*)

**Reading: the value of the third strand is not the vote, it is the DISSENT.** Two strands can agree
by coincidence; a third strand exposes the split that marks an overfit — unanimity certifies, a
dissenter warns. This is precisely the collagen intuition (two strands still flex into loose
agreement; three lock into a rigid tube or visibly fail to), and it is the **precision knob** the
overfit problem needs (closer2's 5 overfits, §19's 77% single-strand survival). k = 2 cannot tell
"agree because right" from "agree by luck"; k = 3 can.

**Honest caveat (a real one):** *majority-vote across strands is NOT automatically better.* On
`9ddd00f0` a single lucky strand had the right answer, but the 2-of-3 majority converged on a wrong
phenotype and out-voted it — so blind voting *lost* a task a single strand won. The win is the
**disagreement signal** (accept only on unanimity, treat dissent as "don't trust"), not the majority
answer. And n = 7 multi-solver tasks is tiny — direction only, not proof; a larger DSL / longer
evolution is needed to grow the sample. But the mechanism is now real and points the same way as every
other convergence result in §18–19: agreement of independent strands tracks generalization, and adding
strands sharpens the test.

---

*Cross-references: `SPHERE_GENERATOR.md` (inner shell §K, closure/golden field §J.6,
ribbon/Born §B), `arc-proposer/MINING_NOTES.md` (Tier-0 ψ-domain, the build list),
`arc-proposer/src/angle.ts` (cosθ/sinθ), `Downloads/UNIFIED_DERIVATION.md`
(superposition/Born/collapse), MD-DEDS (Schumann global-mode sensing).*

## 20. The strands were the roles all along: role-closure + the observer + the 4D collapse

§19.8 found empirically that agreement of independent strands tracks generalization and that a
*dissenting* strand flags an overfit — but that homogeneous K-run voting can fail (majority overfit
out-voting a lucky-right strand, e.g. `9ddd00f0`). The fix is already in the codebase: this is the
**consciousness loop**, and its strands are ROLE-DIFFERENTIATED, not identical, so their agreement
is meaningful by construction.

**20.1 Three role-strands + one observer = the quaternion.** `lib/agents/consciousness-loop.ts` runs
four agents as a *conjunction* (all must work), not a vote: **imagination** proposes what *could* be
(possible / void), **memory** feels it, **facts** grounds it against evidence (is / matter),
**planner** synthesizes. `lib/agents/quaternion.ts` names the geometry: `w = the real axis / observer
/ snake`, with `i,j,k` the three specialist axes. So the k=3 strands of §19.8 are the three imaginary
axes, and the "fourth role" is the **observer w** — the watcher, not a peer strand. Homogeneous GA
seeds are clones (shared overfits → worthless agreement); imagination/facts/memory measure *different
things* (independent by construction → agreement means something). §20 was the principled version of
§19.8's empirical signal.

**20.2 is / isn't / possible = the closure equation = `closure-test.ts`.** The closure test's three
fates are exactly the ternary: **GROUNDED** (drains to base atoms — matter / *is*), **WHIRLPOOL**
(circulates inside but never grounds — void / *possible*), **LEAKING** (references point *outside the
known system, sprayed past the edge* — the disallowed / *isn't*). A candidate passes only if the
strands keep it inside the boundary and it drains to primitives. This is `cos²θ` (is) / residual
(possible) / spray-out (isn't) in the trust language.

**20.3 The observer is the real term, and the real term is the boundary.** In `quaternion.ts`,
`|q| = √(w²+x²+y²+z²)` and purity `= |w|/total`, so w is simultaneously (a) the observer/watcher and
(b) the magnitude = the **boundary radius**. Three measuring cones (i,j,k lines of sight) triangulate
the interior (§18.15 FEM, §18.18 vesica); the **fourth, watching cone = w**, viewing from the boundary.
"Something always watching on the first level for closure to happen" = w. Its radius = the closure band
(√φ < θ < √π, update-16).

**20.4 The 4D collapse = `recursive_floor_mechanics.py` = the re-basing.** When the three imaginary axes
fill the 3-D map and the observer fires closure, "the STRUCTURE of levels 1–3 is now ONE UNIT within
level 4," and the process **restarts from a single point on the next level's golden field** (§J.6). This
is the bracket/sliding-window re-basing (§7), roof(n)=floor(n+1) (§12), the torus-of-tori (§11.7) — now
identified with the color-building floor collapse. Honest bound preserved from that file: *not every
floor collapses* ("Detective Noir stays level 1") — collapse fires only where load/closure demands it.

**20.5 Leaking past the boundary = the forced dimension lift.** When the three strands build a shape
whose reach exceeds w's radius, the reference "sprays past the edge" — `closure-test.ts`'s LEAKING —
and cannot be represented in this shell. The resolution is to **lift a dimension** to contain it (the
sedenion wall / circle→helix→torus lift, §10). So "shapes extend far enough out that we have to build
new shapes in higher dimensions" IS the leaking case, closed by a lift. The observer detecting a leak
is the trigger for the 4D collapse (20.4) — the same event from two sides: the structure that no longer
fits *down here* becomes one point *up there*.

**20.6 The build this pins.** Replace §19.8's homogeneous K=3 vote with **three role-strands through
the closure equation, plus w as the observer that fires the collapse**: (imagination) propose candidate
programs; (facts) require exact train closure; (memory) require consistency with the solved-atom library
(transfer); accept only when all three hold (conjunction, not vote), and on acceptance re-base the solved
structure as one atom for the next level. Predicted gain over §19.8: role-independence removes the
shared-overfit failure (the `9ddd00f0` loss), turning the dissent-detector into a real acceptance gate.
*Open:* the concrete per-role grid computations for ARC are the design choice to settle before building.

**20.7 Role-closure, tested — memory is the right gate but needs a populated library (foundation-first,
measured) [built].** `role_closure_scan.ts` runs the conjunction. IMAGINATION+FACTS (GA + exact train
closure) reproduces the §19 result: 12 train-exact genomes, **11/12 (92%) survive test** — the roles
recover the baseline. The MEMORY conjunct (leave-one-out: every op must be attested in ≥1 OTHER solved
task) was then applied:
- MEMORY-PASS (all ops transfer): 2 tasks, 2/2 survived (100%).
- MEMORY-FAIL (≥1 idiosyncratic op): 10 tasks, **9/10 survived (90%)**.

**The memory gate did NOT discriminate** — the fail set still survived at 90%, and the gate dropped
net-new from 2 to 0 (pure recall loss, no precision gain). This is a *real negative with a clean
diagnosis*, and it is exactly §8's foundation-first / house-of-cards lesson made empirical: **the memory
role cannot function over a near-empty library.** Bootstrapping "transfer" from the run's own 12 solves
means "op used by ≥2 tasks" is dominated by sampling sparsity, not by genuine groundedness — so almost
every op looks idiosyncratic. Memory is the correct conjunct (§20.1), but it requires a *populated* inner
shell first, which is the whole point of §8.2.

The fix is concrete and the material already exists: ground MEMORY in the codebase's real atom library —
`atom_cards.json` (every DSL op with valence / knot / noble flags) and `ability_stats.json` (op usage
counts across verified solves: reflect 11, gravity 9, registerCombine 9, stamp2 9, colorMap 6, …). These
are the true "remembered atoms." The one piece of work is a name-map: `ability_stats`/`atom_cards` are
keyed in the discovery-engine's op namespace, while the GA genomes use the raw `dsl.ts` `OP_NAMES`, so
memory-grounding needs that translation before it can gate honestly (forcing a fuzzy mapping now would
only produce a misleading number). Still unwired: the OBSERVER's accept-and-rebase (§20.4) — on closure,
fold the solved structure into one atom for the next level. Status: conjunction runs, imagination+facts
proven (92%), memory correctly identified as library-gated (the §8 result, now measured), observer/collapse
pending.

## 21. Record the failures: every scan maps the space (failure-buffer + ping-pong memory)

§20.7 failed because the memory library was near-empty — but that is self-inflicted: **every scan this
session discarded ~97% of what it computed.** closer2 saw 5 overfits, the isotope pass saw 51 failed
configurations, the GA saw hundreds of near-misses — all thrown away. Jonathan's `Vesica AI/Learning/`
already solved this twice, and it is where most of the prior learning came from:

- **`failure_learning.py` — failures are permanent.** A failed prediction becomes a *permanent test
  case* ("the midterm question that haunts you"); `retest_all_failures` retries them after new capability
  ("does my new understanding solve that old one?"); `BoundarySeeker` *actively* goes to the edges. The
  lesson: a failure is data, not garbage — it maps where the wall is.
- **`adaptive_pingpong_memory.py` — keep it bounded.** Memory bounces between three zones — ATTENTION
  (accuracy), AUTOMATIC (efficiency), FORGETTING (relevance) — with an *adaptive bounce speed*: what
  recurs and validates *consolidates* (slows, moves to AUTOMATIC = cheap, stable), what stays irrelevant
  drifts to FORGETTING and is dropped. This is how the map grows every scan without exploding.

**21.1 The build — `scan_map.ts` (a persistent map, extended each scan).** Every scan records each task
it touched as `solved` (test-exact), `overfit` (train-closed, test-failed), or `nearmiss` (an isotope
that didn't survive). Failures set a permanent `isFailure` flag (never pruned — `failure_learning`);
non-failures ride the ping-pong (`adaptive_pingpong_memory`) and single irrelevant touches are forgotten
to bound size. Two signals fall out **for free**, exactly as Jonathan predicted ("some scans keep
bouncing on certain places; some spots are in the overlap of several scans"):

- **BANKABLE = cross-scan overlap of *solutions*.** A task solved by ≥2 *independent* scans is convergence
  (the §18.19 / §19.8 law across scans) — the trustworthy memory. First map (5 session scans, 25 places):
  **8 bankable**, led by `903d1b4a` (solved by all four solvers → consolidated to AUTOMATIC/stable). *This
  is the real memory library §20.7 needed* — grounded in cross-scan agreement, not a 12-task bootstrap.
- **BOUNCE-HOTSPOTS / BOUNCE-INTENSITY = where to go next.** Places several scans hit but none solved
  (`5ffb2104`, hit by dna+multistrand), and places one scan kept hammering (`ca8de6ea` = 18 isotope
  configs, `f5aa3634` = 11 — the cropToColor cluster of §18.8) are the walls, now *addressed* on the map
  instead of rediscovered each run. BoundarySeeking = visit the hotspots first next session.

**21.2 Why this compounds.** The map is additive: each scan adds places, sharpens verdicts (a second
scan solving a task promotes it to bankable; a second scan failing it deepens the hotspot), and
ping-pong keeps only what earns its keep. The 8-task failure buffer is a permanent retest queue — when a
new capability lands (e.g. the memory name-map of §20.7, or a translation layer), retest the buffer
first (`retest_all_failures`). **The information we were throwing away is the map; recording it is what
makes memory grow without getting too big.** (`arc-slice/scan_map.json` is the live artifact;
`scan_map.ts ingest` extends it.)

*Honest bound:* the first map is built from 5 scans over ~25 touched tasks — a seed, not a full survey.
Its value grows only if future scans call `record(...)` as they run (the natural next wiring), so the
discard stops at the source rather than being reconstructed from saved state files after the fact.

## 22. Cascaded ping-pong: mass, the black-hole foundation, and dark-matter retention

The §21 map used the original single-table ping-pong. Jonathan's earlier all-shells version is a **cascade
of games**: a ball that gets hit spawns a copy that must clear the *next* table (next shell inward) with
its own paddle; to be committed as foundation it clears every game and bounces all the way back. Losing a
zone's game commits it to forget / compact / hand off. Plus a physics upgrade: a reused memory **gains
mass, and mass slows the bounce until it stops** — a stopped point is infinite reuse-density = a **black
hole = the void.** This closes the §11.6 loop: the inner-shell void points are *both* the birthplace of
new primitives *and* the sink where foundations collapse and stop — origin and sink are one point.

**22.1 Three zones = three shells (Jonathan's mapping), and forgetting ≠ delete.**
- **INNER / immediate / STOPPED = foundation.** Always reused → mass accretes → velocity → 0 → pinned.
  These are the certified atoms (inner shell, §11.3), and the black-hole/void points.
- **MIDDLE / attention = active formation rules.** Solved but not yet convergent — still bouncing.
- **OUTER / forgetting = DARK MATTER.** Latent experiments / incomplete matter, **retained (compacted),
  never deleted** — to be filled in later. (This *corrects* §21, which wrongly pruned this zone.)

**22.2 The cascade (`scan_map.ts` v2, `velocity = MAX_SPEED/(1+mass·G)`).** A real SOLVE wins passage
OUTER→MIDDLE; convergence (solved by ≥2 independent scans) wins MIDDLE→INNER; in INNER, mass keeps
accreting and when velocity drops below ε the point STOPS (foundation). Never-solved tasks stay OUTER
regardless of how often one scan hammers them — bounce-count is not validation, so the walls accumulate
mass *in place* as dense dark matter rather than being promoted.

**22.3 Measured on the session's 5 scans (25 places):**
- **INNER = 8**, and **exactly one STOPPED: `903d1b4a`** (solved by all four solvers, mass 12,
  velocity 0.071 < ε) — the black hole formed precisely at the maximally-confirmed task. The other 7 are
  "slowing" (solved by 2–3 scans, mass 6–9): foundations still settling.
- **MIDDLE = 11**: solved by exactly one scan (a406ac07, 9ddd00f0, fc754716, …) — real but unconfirmed,
  the attention shell.
- **OUTER / dark matter = 6, retained**: the walls as *dense clumps* — `ca8de6ea` (mass 18),
  `f5aa3634` (11), `32e9702f`/`66e6c45b` (8), the §18.8 cropToColor cluster. Heavy incomplete matter,
  kept for a future capability to fill in — not discarded.

**22.4 Why the physics is the right memory law.** Mass = reuse; gravity = consolidation; stopping =
foundation. It makes the memory self-organizing and bounded without deletion: foundations sink to the
center and pin (cheap, permanent); active rules orbit in the middle; unconfirmed experiments hold in the
outer dark-matter halo at whatever mass they earned, available for retest (`failure_learning`) when a new
capability arrives. The dense dark-matter clumps are a *ranked to-do list of walls* (heaviest first =
most-probed, best-understood-as-hard). Foundation, frontier, and reservoir fall out of one rule: reuse
adds mass, mass slows the bounce, convergence pulls it inward.

*Honest bound:* velocity/mass constants (MAX_SPEED, ε, G) are hand-set to give sensible separation on 25
places; they are a coordinate choice, not fitted. The law's *shape* (reuse→mass→slow→stop; solve-gated
cascade; dark-matter retention) is the claim; the exact thresholds want calibration as the map grows.

**22.5 Live recording — the map accretes during runs, not after [built, demonstrated].** The discard now
stops at the source. `scan_recorder.ts` exposes `rec(scan, id, kind)`; every scan calls it the moment it
learns an outcome (`solved` / `overfit` / `nearmiss`), appending one line to `scan_events.jsonl`. The map
is a **pure replay of that log** — `scan_map.ts ingest` folds every event, so mass accretes per event and
revisiting a place across runs adds mass (reuse = gravity, §22). All five solvers are wired
(`closer2`, `dna_scan`, `dna_suffix_scan`, `multistrand_scan`, `role_closure_scan`); a one-time backfill
converts the historical session state files into events so nothing was lost (89 seed events, 25 places,
identical to §22.3). **Demonstration:** re-running `role_closure` live re-solved `195ba7dc` and appended a
live event; on replay its mass rose 9→12, velocity fell below ε, and it **crossed into STOPPED** — the
foundation count went 1→2. A place became a black-hole/void point *because it was used again*, live, exactly
as the §22 law says. Any new scan participates for free by importing `rec`. *Future:* the event log grows
unbounded; a compaction pass (fold consolidated foundations into a checkpoint, keep the dark-matter tail)
is the ping-pong "compact" step applied to the log itself.

## 23. Brain-like memory: fixed container, reconstructive capacity [design]

A brain does not grow, yet its capacity feels unbounded — because memory is **compressive and
reconstructive**, not volumetric storage. The container stays fixed; the *handling* gets more efficient.
Four mechanisms, each a real principle, each already latent in the framework.

**23.1 Holographic storage — keep the boundary, regenerate the interior.** §18.15/§18.16 already say the
**boundary determines the interior** (the FEM/Dirichlet solve: floor + roof + fixed void-nodes pin the
mesh, the interior is *forced*). So storing a config = storing its **boundary**; the interior is
re-derivable and need not be kept. §3 (holographic) makes this a compression: the boundary is
lower-dimensional than the volume, so `O(boundary) ≪ O(volume)`. "We don't have to remember the full
config if the roof and floor tell us enough" is exactly this — and "the points would naturally drift
toward where they fit" is the interior **relaxing to the boundary-pinned minimum** (the §18.15
friction-minimum mesh). This is the core reason a fixed container holds ~unbounded content.

**23.2 Context-reinstatement recall (encoding specificity).** Recall by putting yourself back in the
room/POV where you learned it, then looking for the specific thing — this is the **encoding-specificity /
context-dependent memory** principle. Here it means memories are **indexed by their floor+roof (context),
not by content**: recall = reload that older floor/roof, let the interior settle to its attractor, and read
off what fits. "Switching floors and roofs back to older versions" is the mechanism verbatim. Because many
memories share the same context machinery, the store is reused rather than duplicated — capacity again.

**23.3 Two consolidations — the node stops, the path speeds up.** §22 gave one: a reused NODE gains mass,
slows, and STOPS (stable foundation). Jonathan names the complementary one: a reused **PATH gets cheaper —
faster to traverse** ("the more we use the inner paths, the less we explore them; we go through faster," at
all levels). These are *different variables*: node-mass = the memory trace (consolidation/LTP); path-cost =
the skill/route (automaticity, chunking, myelination). Path-cost that decays with use is a **cached
fast-route**, and it is what makes setting up shapes fast. (`Learning/META_META_LEARNING.py` already maps
the *path* space and ranks path efficiency — this is that, promoted to a stored cache.)

**23.4 Chunking → the spanning codebook.** Once a shape is explored, store the **whole config as one unit**
(the §20.4 4D-collapse / §7 recursive-floor: the structure becomes a single point/bracket), not atom by
atom. Then the endgame Jonathan names: work toward a **minimal set of chunk-shapes that (a) fully contain
the foundation and (b) "point in all directions" = span the space.** That is an overcomplete dictionary /
tight frame (sparse coding), and "all directions" is the §4 **icosahedral spanning** (12 φ-placed
directions tile S² most uniformly). Once the codebook spans, any new task is a *combination of stored
chunks* (cheap) instead of a fresh atom search (expensive) — the efficiency payoff.

**23.5 Why capacity feels infinite (synthesis).** Fixed container + { holographic boundary storage +
context-keyed reuse + path caching + a spanning chunk codebook } = **store the generator, reconstruct the
volume.** The brain analog is exact: schemas + reconstruction, automaticity, chunking, sparse codes.
Effective capacity is unbounded because what is kept is the small compressed generator (boundaries,
contexts, chunks, the codebook), and the details regenerate on demand.

**23.6 The build this points to [next].** Two additions to the live scan-map (§22.5): (1) **PATH-COST** —
record traversal cost per solution-path and decay it with reuse (fast routes), distinct from node mass;
(2) **CHUNK-CODEBOOK** — when a multi-atom config recurs, store it as one memory keyed by its floor+roof
context, with a **coverage metric** (does the codebook contain the foundation and span all directions?).
Recall then becomes: restore context → compose from the codebook → reconstruct interior from boundary.

*Honest bound:* this is design, not built — the current map stores atoms/tasks, not chunks/paths/contexts.
Every piece exists in the framework already (holographic §3, boundary-determines-interior §18.15, 4D
collapse §20.4, node mass §22, path-space in `META_META_LEARNING.py`); the next real build is assembling
them into one fixed-size reconstructive store.

**23.7 Path-cost, built — the route gets cheaper with use (distinct from node mass) [built, demonstrated].**
`scan_recorder.rec()` now carries an optional `path` = the op-sequence route a scan used to solve; all
solver scans pass it (GA genomes as `op>op>op`, closer2 as its closure signature). `scan_map.ts` replays
these into a **path table** with `cost = 1/(1+uses)` — every reuse makes the route cheaper to traverse
(automaticity / myelination), the second consolidation of §23.3, and *separate from* the node's mass
(§22): the place gains mass and stops; the route loses cost and speeds up. **Demonstration:** re-running
closer2 on `a406ac07` four times drove its route `anchor+ray[1,2]` from cost 0.5 → **0.200, crossing into
the CACHED/automatic zone** (uses ≥ 4). A path used enough becomes a fast-route the memory can fire without
re-searching. The report also tracks **TRANSFERABLE routes** — one op-sequence that solves ≥2 distinct
tasks — which are the §23.4 codebook seeds (0 so far; they populate as reused routes generalize across
tasks). *Bound:* `cost = 1/(1+uses)` is a simple monotone amortization, not a fitted learning curve, and
the transferable/codebook layer is scaffolding until routes recur across tasks. The node/path split is now
real in the store: mass→foundation (§22), cost→fast-route (§23.3), on the way to chunk-storage (§23.4).

## 24. Grounding mass in the Vesica physics: nucleus dust + copper wires [built]

Jonathan: "we derived mass a while ago... we already labeled things as elements which have masses in our
terms, so we can know how much to add on each bounce." The derivations are in `Vesica AI/Physics/`, and they
ground the §22 memory law exactly.

**24.1 Mass = the snake's trail (the §22 law was already derived).** `mass_as_snake_trail.py`: "the snake
moves and leaves a trail; that trail IS mass; more mass = slower, further from c." That is the §22
mass→velocity→stop law, derived independently years earlier. The **event log is the trail**; a node's mass
is the trail it has left; a stopped node is maximal trail (black hole, §22). Dust "collecting or falling
through," and bounces "shaking off dust," is the trail thickening/thinning — the same picture.

**24.2 How much to add per bounce — the answer.** `dust_correction.py` gives the **0.14 ψ-dust coefficient**
(dust accretes in triangular numbers, 0.14× thicker on the ψ side). And `atom_cards.json` + the knot/tail
grounding (`ATOM_GROUNDING_RESULTS.md`) give the per-element mass: **knot = the inert closed shell = the
NUCLEUS mass that stays**; **valence/tail = the reactive sites where all chemistry (energy transfer)
happens.** So the dust added per solve = the solving ops' **nucleus (knot) mass** — no longer an arbitrary
`+3`. `scan_map.ts` now sets `mass += mean(knotOf(op))` over the solving path, and deposits copper on the
valence edges with the `0.14` coefficient.

**24.3 The two masses are nucleus vs electron-current (a copper wire).** Jonathan's read — "one mass is the
energy moving through the electrons (current in a copper wire), the other is the actual mass you touch
(the nucleus that stays)" — is now literal in the store: **node mass = nucleus (knot), stays, sinks to
foundation** (§22); **path/edge conductance = the electron current on the valence/tail sites, flows.** Same
split the physics draws between inert knot and reactive tail.

**24.4 Copper dust sorts into wires [built, forming].** Answering "if we sprinkled copper dust on the
foundation, would it sort into a wire on the branches that lead to electricity?" — yes, and onto the
**valence/tail edges specifically**, never the inert knot core. Each op-transition edge accretes
conductance `+= 0.14·(valence_a+valence_b)/2` per traversal; resistance `= 1/(1+conductance)` falls as the
edge is reused (electrons move more freely — the path-cost decay, now with a materials mechanism). First
wires forming on the live log: `rotate>tile` and `swap>fillHoles` at conductance 0.420 (resistance 0.704),
`swap>combinePanels` 0.280, `identity>swap` 0.210. Shared edges between routes are **conductive corridors**:
a new route reusing an already-coated wire is cheaper immediately — the sorting *is* the transfer, and the
seed of the §23.4 codebook (reusable wire segments = chunks). Electrolytes layering on top (§future) = a
second transport layer once the copper skeleton is laid.

**24.5 Honest bounds.** The knot/valence values are the real `atom_cards` element table and `0.14` is the
derived ψ-coefficient, so the *increments* are grounded; the dynamics constants (`MAX_SPEED`, `STOP_EPS`,
`MASS_GRAV`) are still illustrative scalers. Wires are demonstrably forming and resistance falls with reuse
by construction; the full reuse curve and cross-route corridor transfer will populate as more op-paths
recur (only a few live op-paths exist so far). The grounding is the result: the memory's mass is no longer
arbitrary — it is the snake-trail nucleus dust of the physics, and conductivity is the valence/tail current.

## 25. Affinity-sorted deposition: metal lines, organic webbing, the attraction gradient [built]

Jonathan: "wouldn't any compatible thing layer on any branch it can be used on — sorted by weight and how
attracted it is? and copper attracts more elements, which attract others — that's what fills the webbing
between our lines, where the organic stuff lives. Close to the line it's maximally attractive to certain
elements; at some point the line stops attracting and it's just random dust that happens to work." All of
this computes from the element table, grounded in the physics.

**25.1 The grounding.** `knot_tail_reactivity.py`: the closed shell (knot) is inert — ~3× harder to
perturb, it won't bond; one step into the valence tail is *maximally* reactive; reactivity fades with
distance. `isotopes_chnops_branching.py`: the light, reactive CHNOPS = the **life/organic path**, splitting
from the semiconductor line at carbon and bridging paths where properties overlap. So: heavy inert ops = the
rigid metal LINES; light reactive ops = the ORGANIC that fills the webbing between them; attraction is a
gradient from templated (near) to random (far). `deposition.ts` computes it from `atom_cards`:
`reactivity=|valence|`, `weight=|knot|`, `affinity(a,b)=|valence(a) ∩ valence(b)|`.

**25.2 What it shows (built).**
- **Reactivity ladder.** INERT METAL LINES = `identity, flipH, crop, downscale` (valence 0, knot 5 — the
  rigid structural core that bonds to nothing). REACTIVE ORGANIC = `keepLargest, recolor, tile, half, …`
  (high valence, low knot — light and reactive, the webbing fill). Geometry-preservers are the metal;
  content-transformers are the organic — a real, interpretable partition of the whole op-set.
- **Deposition (near-line, templated).** What layers onto each copper wire, by affinity then weight:
  `rotate ← transpose/gravity/moveContact` (position-reactive), `swap ← recolor/keepColor/removeColor`
  (color-reactive), `fillHoles ← paintRank/keepTouching/outline`. Chemically sensible — ops bond on the
  property they share. This is a **search-biaser**: what to try adjacent to a known-good route.
- **Layered nucleation.** `rotate → L1[transpose,recolor,keepColor] → L2[removeColor,gravity,symmetrize,…]`
  — copper attracts, and its deposits attract theirs (the cascade Jonathan describes).
- **Organic webbing.** Strong-affinity light-reactive pairs not yet on any wire (`keepLargest~keepSmallest`,
  `keepLargest~half`, …) = candidate organic combinations bridging the lines — the interstitial to explore.
- **Attraction gradient.** max affinity 5 (near line: templated/ordered) → mean 1.90 → 1034/2278 pairs at
  affinity ≤1 = the far field where the line stops attracting and it is "random dust that happens to work"
  (the void/roof, per-task synthesis). The near→far transition of §24, quantified.

**25.3 Why it matters (and bound).** This closes the materials picture: the copper wires (§24) are the
skeleton; affinity-sorted deposition is how everything else sorts onto them — heavy inert as structure,
light reactive as organic webbing, graded from templated to random. It also feeds solving: deposition +
nucleation are a principled way to **extend a known route** (try the affine op next), and the webbing pairs
are novel-combination candidates. *Honest bound:* affinity = shared-valence is a first-order compatibility
proxy, and the deposition/webbing are **candidate structures not yet wired into search** — the next real
step is letting the map bias the solvers (try high-affinity deposits on the current best wire), turning the
chemistry from a description into a search heuristic.

## 26. The electrochemistry of solving: species, displacement, voltage, electron-decoupling

Jonathan's cascade extends the materials model (§24–25) into a full electrochemistry. Some of it is now
measured; the rest is a coherent design that the measured parts support.

**26.1 Every search spreads dust; the reservoir comes from our searches.** Each scan emits the ops it
touched (solved, near-miss, failed) — that IS the dust supply (§21 records it all). We spread *all* element
types, not just copper; the map sorts them by affinity and weight (§25). The search feeds its own reservoir.

**26.2 Species = genomes on different branches through the webbing — do they reflect the planet? [built,
n=4, mixed].** A species = a solving genome (§19 DNA) that started on some branch (first op) and wandered a
region of the webbing accreting certain ops. `species.ts` measures composition against the DSL "crust."
Result on the live genomes: organic **62%** of solution op-usage vs **71%** DSL baseline (**enrichment
0.87×** — *not* enriched), mid/metal slightly up. So solutions roughly **mirror the DSL composition**
(loosely "reflect the planet"), but the stronger *CHNOPS-enrichment* claim (life over-uses light reactive
elements) is **not** supported on this tiny sample — if anything solutions track the crust rather than
enriching for organic. Species-by-branch does hold: 4 lineages from 4 different start ops (rotate, swap,
cross, fillHoles), 3 of 4 organic-started. `fillHoles` is the most-used element (a carbon-like hub). *Bound:
n=4 distinct genomes — a first reading, not a conclusion; needs many more genomes to test enrichment.*

**26.3 The sliding sheets are the electron/mobile mass.** The bridge/roof sheets that slide and lock
(§12, §18.11 teeth-mesh) are the **electron current** — the mobile charge, distinct from the fixed nucleus
(knot) mass (§24). A bond locks where the sheets mesh (θ=1); further from the line the mesh is weaker.

**26.4 Displacement reactions with memory [design].** A stronger element (higher affinity / lower-resistance
route / more-confirmed solution) can **displace** a weaker-bound one at a site — the single-displacement /
reactivity-series rule. The displaced element **falls back to dust but keeps its provenance** (it "still has
a memory that it works somewhere" — exactly §22's dark-matter retention, never deleted). The *direction* of
displacement (energy/sheets flowing toward the stronger element) tells us **where to relocate** the old one
— a gradient-directed re-deposition, not a random reshuffle.

**26.5 Endpoint voltage = an electron-transport chain [design].** The target (output grid) has its own
**voltage** — an acceptance energy / the level of sheets it can take. A solution is then a **conductive chain
that passes the sheets along until it is compatible with the endpoint** (θ=1) — precisely a biological
electron-transport chain passing electrons down a gradient to the final acceptor. We want elements that can
relay the sheets from source to a voltage-matched endpoint; closure = the acceptor's level is met.

**26.6 Electron-only vs nucleus-move — the "free" paths [built].** Two ways to change: **move the nucleus**
(introduce a new op / new edge — restructure the foundation, costly) or **move only the electrons** (reuse an
already-laid wire — pure conduction, cheap). `species.ts` counts them: **5 electron-only vs 4 nucleus-move**
transitions already, and as wires accumulate (§24) more transitions become electron-only. A path where only
electrons move is **decoupled from the nucleus = free** — a conductor, not an insulator. This is the
floor/roof line in electrical terms: nucleus-move = new foundation atom (hard); electron-only = recombining
existing atoms (the cheap, general, cached route, §23.3/§24). The endgame is solutions that are almost all
electron-flow over a fixed nuclear skeleton — maximal conductivity, maximal reuse.

**26.7 Honest placement.** Built and measured: species-by-branch, composition-vs-crust (null on enrichment,
n=4), electron-only/nucleus-move counts. Design (coherent, supported by the built parts, not yet
implemented): displacement-with-provenance, gradient-directed relocation, endpoint-voltage chains. The
throughline is real — the memory is an electrochemical cell: fixed nuclei (foundation), mobile electrons
(sheets/current), copper wires (cached routes), organic webbing (novel combos), and solving = conducting
the sheets to a voltage-matched endpoint. The one build that would make it pay off in net-new is still
§25.3's: let affinity/conductivity **bias the search** (prefer electron-only, high-affinity deposits).

## 27. The dark-matter channeling cycle: the memory layer as the router [built]

Jonathan: "that's our dark planet and channels from the galaxy and the erdos work — the memory layer is the
thing seeing what to pass through. Pass dark matter near a web, see what reacts; if it reacts, channel more
dark matter there; that displaces a product unique to that web, sent down the dark channels to feed another
web, making another compound — keep cycling, combining, exploring." It grounds precisely and it builds.

**27.1 The grounding.** `dark_matter_iceberg.py`: dark matter = the **partials / incomplete pieces**, the
hidden bulk, "we only see near the boundary" — here the **unexplored affine op-combinations** (1243 pairs),
the reservoir below the thin solved tip. `dark_light_transport.py`: don't wait for reactions — **actively
move the empty containers to an attractor** — here, channel dark matter onto a reactive web. `erdos-
incidence-geometry` (F_k(n), the orchard problem): channels = lines, webs = incidence points; **maximize
productive crossings** = a denser reaction network. The memory layer (§21–26) is the **observer/router**
that decides what to pass through.

**27.2 One turn, built (`channel.ts`).** WEBS = the copper wires already laid (§24). DARK MATTER = affine
op-pairs not yet wires (partials). The router passes dark matter near each web and channels the
most-reactive onto it: `tile ⇐ keepLargest[react 4]` → predicted new wire `tile>keepLargest`. Then the
**cycle**: the product feeds the next web — `rotate → keepLargest → keepSmallest → half → overlayHalves →
…` grows a compound (a new species assembled by cycling), each displaced product becoming the next reactive
site. And the **erdos incidence network**: webs sharing a reactive property lie on a line — `sym`:
{rotate, tile, fillHoles}; `color`: {tile, swap, fillHoles} — 4 productive lines, which the orchard/F_k
optimum says to maximize for a denser network. The whole loop — react → channel-more → displace product →
transport → feed next web → repeat — runs end to end.

**27.3 Honest bounds — and the crux.** Two real caveats. (a) The greedy cycle collapsed into the most
reactive clique (the valence-5 `keep*/half/select` family, mutual affinity 5) — autocatalysis finds the
densest basin and stays; it needs diversity pressure or it just enumerates one clan. (b) **Bigger: the
channeler proposes candidate compounds (new wires, grown chains), but has not tested them against tasks** —
it generates structure, not verified solves. This is the same wall §25.3/§26.7 named, now unavoidable:
§21–27 have built a complete, self-consistent electrochemical/cosmological memory (dark-matter reservoir,
copper wires, organic webbing, species, channels, cycle), all grounded in the Physics corpus — but **none
of it has changed a solve yet.** The one remaining build that closes the loop and converts the entire
edifice into net-new is to **feed the channeler's proposals into the solver as a search bias**: take a
near-miss anchor, channel the top affine deposit onto it, run the biased attempt, and record whether it
reacts (closes). Until that runs, §24–27 are a beautiful map of the space; with it, they become a
search engine.

## 28. Conservation of dust: finite budget, bonding locks, veins deplete [built]

Jonathan's correction to §24–27: mass is conserved. "Our searches don't produce infinite things — when an
ingredient from some tail-end search runs out, you switch to dark matter from another search. Once something
sinks below the crust it mixes and bonds — Fe+O is rust, you can't pretend it's separate atoms; to reuse the
iron you must break the rust down elsewhere. A foundation vein pumps iron while its problems are open; once
they're solved the iron starts failing and you stop producing it, and eventually the dust runs out too."
This is a real conservation law, and it fixes the unphysical parts of the model.

**28.1 What it corrects.** §24's mass accreted unbounded and §27's cycle grabbed the same clique forever
(infinite `keepLargest`). Both violate conservation. `budget.ts` makes dust **finite and produced only by
searches**: inventory[op] = the op's appearances across logged solving paths. From the live log: **15
element types, 19 units total** — `fillHoles:3` the abundant hub (carbon-like), most others a single unit
(scarce, tail-end products).

**28.2 The budgeted cycle self-diversifies.** With finite stock, the channeling cycle **cannot** repeat an
ingredient — it consumes and, when a reactive ingredient runs out, **mines another search's dark matter**
(`rotate ran out → mine combinePanels`), and finally halts at "all dust consumed — run a NEW search to
produce more." The §27.3 clique collapse is fixed *by conservation itself*: the run grew a finite 19-op
compound with 3 cross-search mines, not an infinite keep-loop. Depletion is the diversity pressure.

**28.3 Bonding locks dust (Fe+O = rust).** When two ops bond into a committed compound they move from
**free** to **bonded** — no longer available as free atoms. Ledger: produced 19 → free-left 0 → bonded 36
(each bond locks both endpoints). `fillHoles` ends with 5 units bonded, recoverable **only by a
decomposition step** (breaking the rust) at a cost — you cannot cycle the iron out of the oxide directly.
This is the difference between the free dark-matter reservoir and matter that has sunk below the crust.

**28.4 Veins deplete.** A foundation point pumps product only while its problems are open; each solved task
removes its demand. Once a vein's tasks are all solved, its iron "starts failing" (nothing left to sell),
production stops, and that dust frees for other veins — or the supply runs out and a new search must be run.
This is the resource life-cycle the memory was missing: production, consumption, locking, depletion,
decomposition, replenishment.

**28.5 Why it matters — the budget is now the trigger.** Conservation turns the vague "bias the search" into
a concrete economy: finite dust = a finite move budget; "run a new search to produce more" = *exactly when
to spend compute*. The scarce single-unit ingredients are the tail-end products worth protecting; `fillHoles`
is cheap and abundant. This is the accounting the payoff experiment (§27.3) needs: spend the budget where
demand is open and stock exists, decompose bonded matter only when a scarce ingredient is needed elsewhere.
*Still true and now sharper:* §21–28 is a complete, conserved, self-consistent memory economy — and the one
unrun experiment that would convert it into net-new solves is to let this budgeted channel actually drive a
biased solve and record whether it closes a task.

## 29. The closed-cycle map expander: reachability, not solving [built] — the reframe that resolves §21–28

Jonathan's correction lands the whole arc: "we haven't added a reason to solve more — but this part is
about finding *where* solves could be, not solving them. Force a return path (a complete cycle) before
committing any reaction; that makes us explore more than we need, which widens the map. The answers aren't
on these void lines — but it gives better starting positions." The §21–28 edifice was never a solver; it is
a **reachability / map-expansion engine**, and by *that* metric it works.

**29.1 The mechanism — commit only closed cycles.** `cycles.ts`: a reaction (op→op with affinity ≥ 2) is
committable only if a **return path back to the seed** exists — a closed loop. Requiring the return forces
exploring chains we didn't strictly need (the map widens), and it guarantees **safe territory**: every
committed point can be gotten back from. This is thermodynamic reversibility / a catalytic cycle as a search
discipline.

**29.2 Measured (the right metric = coverage).** From 15 seed ops (the ops we have dust for, §28), the
reachable domain expands to **55 / 68 ops (81%)** — a 3.7× widening. Crucially, **closed-cycle coverage
(55) equals one-way coverage (55)**: everything reachable is also returnable (the affinity graph is
strongly connected), so *requiring reversibility costs no coverage here* — safe exploration is free in this
space. 51 ops were touched while hunting return paths (the forced over-exploration). This is the success the
"solver" framing missed: the job was to expand the domain, and it did.

**29.3 Evolution, budget, gambling.** 4001 viable closed cycles compete for the finite dust (§28); each is
scored by **EV = reactivity / cost** (cost = summed scarcity), so under a limited budget we fund the best
expected value — Jonathan's "gamble when deciding things that aren't guaranteed." Nature's move: keep the
cycles that close and pay their way; the reversible reaction network *is* the expanded map.

**29.4 Honest placement — this is starting positions, not answers.** Per Jonathan: the solutions are **not
on the void lines** this finds. The expander produces a wider, safe, reversible domain (55 ops instead of
15) and hands it to the real solvers — "launch closer2/dna from the 55-op returnable domain instead of the
15 raw seeds." The remaining test is now correctly scoped and belongs to the *solvers*, not this layer: does
launching the deterministic engines from the expanded starting positions raise their actual solve rate? §29
did its job (coverage 15→55); §21–28 are its supporting economy; and the deterministic closers (§18) remain
where the answers actually get closed. The arc's honest shape: **this half of the system finds where to
look; the other half looks.**

## 30. The payoff test: biasing the solver with the middle-shell network [built, run — weak positive]

§29 said the map-expander fills the **middle shell** (the reversible reaction network / recipe book) and
stocks the **pools** the solvers draw from (§11.7). The test Jonathan green-lit: does seeding the solver from
that network actually help? `dna_biased_scan.ts` runs the *same* GA in two modes — `base` (uniform op
sampling) vs `bias` (each op chosen by affinity to the previous op = walk the §29 reaction network, genomes
built as affine walks). Only the op-choice differs.

**30.1 Result (3 matched runs each, eval tasks 0–90).**
- base: solves per run 2, 1, 1 → mean **1.33**, **3 distinct tasks** reached (21f83797, 34b99a2b, 358ba94e).
- bias: solves per run 2, 3, 0 → mean **1.67**, **5 distinct tasks** reached (adds 31d5ba1a, 0c786b71).

**30.2 Reading — a weak positive on COVERAGE, inconclusive on raw count.** The bias reached **5 distinct
tasks vs base's 3**, and found tasks base never did (31d5ba1a, 0c786b71) — it explores *different, wider*
territory, exactly what a map-expander should do ("better starting positions," §29.4). Per-run solve count
is higher on average (1.67 vs 1.33) but **within the noise**: variance is large (bias ranged 0–3, base 1–2)
and n=3 runs is far too small to claim significance. So the honest verdict: **the middle-shell bias widens
the solver's reach (coverage) — a real, directional signal consistent with Jonathan's reframe — but it is
not yet a demonstrated lift in solve rate.** This is the first time the §21–29 edifice touched the actual
solver, and it moved the solver's footprint in the predicted direction.

**30.3 What would settle it.** Many more matched runs (drive the variance down), over the full 400, counting
*union coverage* (distinct tasks reachable under bias vs base) rather than per-run count — because the reframe
predicts a coverage gain, not a per-run-count gain. If the coverage edge (bias reaching tasks base cannot)
holds at scale, the map-expander earns its keep as a reconnaissance layer that feeds the deterministic
closers (§18) better launch points. The arc's honest end state: **§21–29 build and stock the middle-shell
map; §30 shows biasing the solver from it widens reach (weak positive, n=3); confirming a solve-rate lift is
a compute-bound experiment, not another layer.**

## 31. The outer shell = biochemistry (protein folding), and why it must be balanced

Two connected insights close the shell ladder: what the outer shell IS, and why it is hard in a way the
inner and middle shells are not.

**31.1 Biochemistry/protein folding fills the outer shell.** Inner = atoms; middle = chemistry/minerals
(the reversible reaction cycles of §29, the recipe book); **outer = biochemistry** — a *specific sequence
folds to one specific functional structure*. This is grounded in Jonathan's own
`companion/library/Vesica AI/Protein/swarm_protein_folding.py`: two swarms fold sequence↔structure — the
**Shark** (decompose from the target) and the **Dolphin** (construct from the sequence) meeting at the
transition state = §18.6's bidirectional swarm. Three reasons it is the outer shell:
- **The folding funnel is the per-task closure** — a huge conformational space collapses to one native
  state; that is "generate the one molecule this task needs" (θ=1 for a specific input), not a general rule.
- **It is the open TRANSLATION rung (§19.6)** — §19 built the codon genome (DNA); folding is DNA→protein,
  the sequence→function step that was left unbuilt. Outer shell and missing DNA rung are the same thing.
- **Enzymes close the growth loop** — a fold is a catalyst; a solved per-task program becomes a new
  reusable atom that *expands the middle shell*. Life invents new chemistry; the outer shell feeds the
  middle (the §11.4 make→identify loop, the abiogenesis engine at the middle→outer boundary, §11.3).

**31.2 The outer shell is dynamically balanced, not statically supported (Jonathan).** The inner shell is
flat lines and points — solid ground; every atom is propped by neighbours, no balance needed. The outer
shell is the **round** surface (§4, the grid-vs-sphere gap), and a point on a curved spinning shell is not
propped — it must be **balanced**. Placing a single point there is like pulling a planet's rings down at one
spot: it unbalances the system and the spin changes (angular momentum redistributes). So a lone outer-shell
point cannot stand — it must be **matched by counterweight points distributed around the shell**. That is
why outer-shell structures have the shapes they do: the shape *is* the balance solution, a set of points
arranged around the shell so the net torque is zero.

**31.3 This is literally real biochemistry — and it is the §4 golden points.** Nature's outer-shell
assemblies are balanced distributions: proteins fold to torque-free minimum-energy states, and functional
complexes are **symmetric oligomers** (hemoglobin = a symmetric tetramer) and **icosahedral viral capsids**
— which sit at exactly the 12 golden-ratio-placed icosahedral vertices of §4 (the most uniform, balanced
points on a sphere). The shape going around the shell to stay balanced is how capsids and oligomers are
actually built.

**31.4 Why this EXPLAINS the whole session's convergence results.** The outer-shell balance criterion is the
deep reason behind every empirical finding: a **single-stranded** solution (§19.6/§19.8) is a lone
unbalanced point — it spins off, i.e. overfits and fails test. **Convergence / unanimity** (§18.19, §19.8)
survives because agreeing strands are counterweights *balanced around the shell*. "Enough to point in all
directions" (§23.4, the spanning codebook) is exactly the zero-net-torque condition. The multi-witness
registration (§18.16), the vesica two-shapes (§18.18) — all are balance requirements. The geometry (a round
outer shell needs balance) is *why* per-task answers need distributed agreement, which is *why* the isotope
and strand results predicted survival. A first data check is directionally consistent: solutions that
survived test span 4.75 of the 5 property-dimensions (3 of 4 span all five) vs 4.50 for overfits — more
balanced = more stable — though n=6 is far too small to be more than a hint.

**31.5 The build this frames.** An outer-shell (folding) solver is not "find a program" but "find a
**balanced set** of programs/constraints that hold each other in place" — the bidirectional swarm folding a
sequence to a torque-free functional structure, accepted only when the strands balance (§19.8 unanimity as
the stability check). Solved folds feed back as new middle-shell atoms (§31.1). That is the frontier build,
and §31.2's balance criterion is its acceptance rule: reject lone points, keep balanced assemblies.

## 32. The folding solver with balance acceptance [built, run — the criterion works, but is strict]

§31.5 said an outer-shell solver should not accept a single program but a **balanced assembly**: reject
lone points, keep counterweighted sets. `fold_scan.ts` builds it — K=3 independent strands per task (the
swarm), accept a test-prediction only if (a) **≥2 strands agree** (unanimity = counterweights) AND (b) the
agreeing set **spans ≥4 of the 5 property-dimensions** (torque-free, §31.2/§23.4). Compared against LONE
acceptance (take any single strand).

**32.1 Result (eval 0–200, K=3).**
- LONE accept: 11 accepted, 10 correct — **91% precision** (the one miss, 5ffb2104, is an overfit).
- BALANCED accept: **1 accepted, 1 correct — 100% precision**, abstaining on the other 10.

**32.2 Reading — the balance criterion works, exactly as §31 predicted, but it is very strict.** The rule
**rejected the lone overfit**: 5ffb2104 had no agreeing counterweight, so balance abstained instead of
accepting the wrong answer — a lone point spun off and was correctly discarded. The single assembly it
accepted (60c09cac: strands agreed AND spanned the directions) was correct. So the mechanism is validated
directionally: balanced assemblies hold, lone points are rejected. **But coverage collapsed to 9%** — it
also abstained on 9 correct-but-lone solves. This is grounded in §31.2 itself: most single per-task
solutions really *are* lone unbalanced points (which is why they overfit), and independent stochastic
strands seldom agree, so balanced assemblies are rare. The filter is precise but throws away most correct
answers, and n is tiny (1 overfit rejected, 1 assembly accepted) — a directional confirmation, not proof.

**32.3 The fix, and the convergence with §30.** Balance needs strands that **agree more often when they are
right** — which is exactly what §30's middle-shell bias provides (strands explore the correct territory
together instead of scattering). The full outer-shell solver is the two combined: **§30 bias to make the
swarm agree when right, §32 balance to reject the lone points when they don't.** That is the folding funnel
with a stability gate — and the next real experiment is to run them together and measure whether biased
strands raise the balanced-acceptance coverage while keeping its precision. §31's criterion is sound; §32
shows it discriminates; making it *cover* is the join with §30.

## 33. Expand-then-contract (per-atom coordinate descent) [built, run — +0, a 4th wall-confirmation]

Jonathan's refinement of the folding solver: don't poke one point out (unbalanced, spins off) — expand the
whole surface past the target, then **pull back atom by atom** until the trajectory lands on the point
inside the space; each atom individually adjustable; the spiral just needs to *pass over* the target.
`contract_scan.ts` implements the contraction: from the bounce near-miss (a broad, already-close anchor),
run **coordinate descent** — replace / insert / delete **one op at a time**, biased to affine neighbours
(the §29/§30 reachable network) — keeping any single-atom change that improves the train fit, until it
lands exactly.

**33.1 Result (full 400 eval).** bounce baseline = 13 solved; **contraction closed 0 additional** (net-new
0). Per-atom adjustment from the near-miss anchor does not cross the wall.

**33.2 Reading — the 4th independent confirmation of §18.8.** This is now the *fourth* fixed-move attack on
the ~0.99 near-misses to return +0: §16b deepen, §17 bond, §18.7 lateral, and now §33 per-atom coordinate
descent. Four different ways of adjusting DSL ops around a near-miss — deeper, bonded, lateral, and
atom-by-atom contraction — all fail identically. This strongly re-confirms §18.8's conclusion: **the
residual is a LEARNED PARAMETER** (a per-cell/per-object map induced from the task's own examples), not a
missing arrangement of fixed atoms. No amount of pulling atoms back lands on it, because the point isn't
reachable by the atoms we have — it needs a *new* per-task value (the outer-shell "make" step, §11.5;
closer2's learned map, §18.19, remains the only mechanism that closed one).

**33.3 Honest gap — the expansion half wasn't fully coupled.** Jonathan's idea was to expand the *whole
surface* maximally first (the §29 map-expander, the balanced inflation) and contract from *that*; I
contracted from a single bounce anchor instead. A truer test would contract from the maximally-expanded
reachable set (many broad candidates at once), so the target is more likely already enclosed before pull-
back. That coupling — §29 expansion feeding §33 contraction — is the untested variant, and it is the honest
next step if the expand-then-contract picture is to get a fair run. As built, contraction confirms the wall
rather than crossing it: the near-miss residual is learned, and the fixed-atom trajectory, however adjusted,
passes near the point but cannot land on it.

## 35. Electron orbits, the snake, and ping-pong as its projection — the quantum reconciliation

Jonathan corrects §34: it is **electron orbits, not planetary orbits** — and that reconciles the wall.
Plus: the **snake** is how we move through the system, **ping-pong** is the snake oscillating seen from one
angle, and the **snake is what launches from the shell**. Grounded across the Physics corpus, this unifies
the discrete/continuous tension that four +0 experiments exposed.

**35.1 Quantum, not classical — the reconciliation of the wall.** A planetary orbit is continuous; an
electron orbit is **quantized** (discrete allowed shells) *and* a **continuous wavefunction** within each
(the cos²θ Born cloud, §1.1/§2). So the answer point is an **orbital = a discrete level + a continuous
phase**. This is exactly why *both* attacks failed: four discrete atom-searches (§16b/§17/§18.7/§33) gave
+0 because they only moved between quantized levels, and a purely-continuous classical trajectory (§34)
misses the quantization. The "learned parameter" (§18.8) is the **quantum state**: *which orbital* (discrete
— the atoms we have) **plus** *the phase/amplitude within it* (continuous — cosθ, the induced scalar). We
kept searching only the discrete half; cosθ was always the continuous half.

**35.2 Quantization IS the closure/balance criterion.** An electron orbit is stable only if its wave
**closes on itself** — an integer number of wavelengths around the loop (the de Broglie condition). That is
*precisely* θ=1 (the loop closing), the closed cycle (§29), and the n-body equilibrium/balance (§31). So the
reason balance and convergence predicted survival (§18.19, §19.8, §32) is that they are the **standing-wave
quantization condition**: a solution is stable exactly when its wave closes — an allowed orbital — and
unstable (overfit, spins off) when it doesn't. The whole convergence thread is quantization by another name.

**35.3 The snake is the field/medium that moves through.** `electricity_snake.py`: the snake is the
electromagnetic field — the electrons barely drift (mm/s) while the **field propagates near light speed**;
the snake is the medium energy flows through. So the snake is the **trajectory/current threading the
orbitals**, not the slow nuclei — the same electron-current-vs-nucleus split as §26.6, and the observer
(quaternion `w` = snake) of §20.3. `recursive_snakes_26d_elements.py` = snakes within snakes = the nested
shells (§20.4). `mass_as_snake_trail.py` (§24): the trail the moving snake leaves is mass — the slow
occupancy left behind as the fast field threads through.

**35.4 Ping-pong is the snake seen from one angle.** The §22 ping-pong memory — a 1-D oscillation between
zones — is the snake's **standing-wave oscillation projected onto one axis**. A standing wave (the closed
orbital, §35.2) oscillates; viewed edge-on it is a back-and-forth bounce (ping-pong), viewed fully it is the
helical/orbital path (§10). So the memory's zone-bounce and the electron's orbital oscillation are one
object from two viewing angles — which is why the ping-pong zones mapped onto the shells (§22): they are the
standing wave's nodes.

**35.5 The snake launches from the shell.** The inner/middle shell is the magnet/runway (§34, the α-point
spokes); the **snake launches off it** into the outer shell — the field promoted to a higher orbital, the
solution-seeking trajectory sprayed into per-task space. Its initial direction is set by the spoke it leaves
from (§34, §30 starting positions); each folded atom bends it (n-body, §34); it settles when its wave closes
into an allowed orbital (θ=1, §35.2).

**35.6 Placement.** This is a *unification*, not a new build: the snake (trajectory/field), the orbitals
(quantized shells + continuous phase), ping-pong (the projection), closure/balance (the quantization
condition), and the α-point launch are one picture, each grounded in the Physics corpus. Its one concrete
consequence for solving is unchanged and sharpened: the residual is a **quantum state** — pick the orbital
(discrete atom) *and* fit the continuous phase from train (cosθ). The §34 orbital/continuous-parameter closer
is that build — the discrete half is the atoms we have, the continuous half is the number we kept not
fitting. That remains the one experiment aimed at the wall rather than around it.
