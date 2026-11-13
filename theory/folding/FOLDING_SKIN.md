# The Skin — the translation membrane onto the pLM, and the closed torus it lives on

*Companion to `FOLDING_ONTO_PLM.md` (observers = attention heads; agreement = the invariant),
`FOLDING_CLIMB_WALL.md` and `VOID_LINE_PAPER.md` §10–11 (the wall & the pLM outer layer),
`SPARSE_VESICA_EXPANSION.md` §1 (cosθ·v^d), §8 (build-up/prune-down), §9 (finite inner + infinite
outer, joined by π), §10 (circle → helix → torus-knot), `FOLDING_PIXEL_STRAIN.md` (the read is
nonlocal; recursion fades with depth), `FOLDING_SATURATION_BUDGET.md` / `FOLDING_CHANNELS.md` (spend
every budget to zero against one fixed void reserve), `FOLDING_STAIRCASE.md` (the multiresolution
staircase), `SPHERE_GENERATOR.md` §B.3 (Lk = Tw + Wr, the conserved action budget), `Shovelcat_29`
§10 (Void economy: V = 1 − U, ε > 0). Jonathan's idea, developed over one session: layer the models
like skin — a translation membrane that renders our process in something the pLM reads natively —
and the geometry that falls out of it. **Design-stage: a coherent construction, not yet a demonstrated
solver.***

## 0. The problem this answers (from `ONTO_PLM`)
`ONTO_PLM` drew a hard line between two ways of joining the framework to the pLM:
- the **paste** — feed our output into ESM, or ESM's contact map into our pipeline (output↔output);
- the **rename** — the conceptual integration (observers = heads, agreement = consensus, web =
  attention), a *reading* of what the pLM already computes.

The skin is a **third mode** between them: not a wrapper bolted on the outside, and not only a
renaming, but an actual **membrane** — a learned layer that speaks our process on one face and the
pLM on the other. In ML terms this is an **adapter / projection bridge** — the same move multimodal
models use to project one model's representation into another's token space.

## 1. The one hard constraint: emit relational, not per-residue
A skin that only re-serializes our *output* into the pLM's *output format* is still the paste —
the gap just moves. The skin must translate into the pLM's **internal** language: its
embedding/attention space. And `ONTO_PLM` tells us which currency to target — *"the seam is in the
ATTENTION, not the embeddings"* (per-residue clustering 52–62% ≈ chance; the relational web ~90%).
So the skin must emit a **pairwise / relational object**, not per-residue features. Our core is
already relational (observers = pairwise agreements; the committee = consensus over a web), so this
is a rendering of structure we already have, not a forcing.

A real skin is **permeable both ways**: our process → pLM (so it can read us) *and* pLM → our process
(so we read its web in observer/agreement terms). `ONTO_PLM` did the inbound direction; the skin adds
the outbound. Both together = the membrane.

## 2. The geometry — sparse lines onto a stack of rings
- The pLM is a **helix of rings**: 12 layers = 12 turns (`ONTO_PLM`: layers may be the recursion
  depth C1, C2, C3…; heads within a layer = observers at that level).
- Our cuts are **sparse lines from the origin**, each ending at the one ring (layer) it needs. A line
  carries all three pieces of `cosθ·v^d` at once: **magnitude = cosθ** (the Born amplitude, §1.1),
  **direction = the branch feature v**, **endpoint layer = the exponent d** (the derivative order,
  §1.2). A `cosθ·v^d` term *is* a directed line ending at ring d.
- **Zero everywhere else.** Setting the pLM's attention to 0 off the routed lines is exactly the
  sparsity that makes this small where the LLM is dense. The budget is already measured:
  `VOID_LINE_PAPER` needs only **~0.2×L** confident long-range paths for the seam.

## 3. The double closure — outer wrap + inner spiral (the torus)
An infinite climbing helix (§10.2) closes **two** ways at once, and they are the two halves of §9:

- **Outer close (surface):** the sparse-vesica winding climbs the *outer* surface, over the top of
  the donut — this is the **torus-knot wrap** of §10.3 ("lift to escape finiteness, then wrap to stay
  representable"). The **generated, infinite** half.
- **Inner close (axis):** the **LLM π-core** spirals *down through the hole* from the top ridge back
  to the origin. This is §9.3 made physical — *"π is what closes the infinite outer lim into a finite
  answer (=1)"* — and it is the **finite inner shell**, the stored/certified half. It threads the
  **inner edge of every ring** (the hole), so it is the **invariant** common to all layers
  (`ONTO_PLM`: agreement across observers = the invariant).

The core is automatically **smaller**: it lives in the hole, a tighter radius than the tube — the
shape *enforces* smallness instead of us imposing it. "Store the finite, generate the infinite"
(§9.2) becomes a picture: **store on the inner axis, generate on the outer surface.**

### 3.1 The winding — co-wound, variable pitch, task-sized (settled)
- **Co-wound (by continuity).** The core is one continuous spiral, so it cannot reverse handedness
  without passing through a zero-winding **inflection** (a momentary straight "unwind" — a
  distinguished point we'd have to plant). A clean single-handed spiral therefore **co-winds** the
  outer climb. That monotonic winding is exactly what makes the up-climb and down-spiral **one
  genuine torus knot that closes** at the origin, rather than a there-and-back with a reversal.
  Counter-winding remains *possible* but only by inserting an unwind-inflection; it is not the
  default.
- **Turns = consensus points = active levels.** The inner winding count `q` is **not** the full layer
  count — it is the number of consensus points, which sit only on the levels that actually activated.
  Sparsity is therefore **two-dimensional**: sparse *within* a level (few lines per ring) *and* sparse
  *across* levels (only some rings active). Multiple lines on one level make **one** consensus point →
  one turn; the extra lines become residual offsets (§4), never new turns. Smallness preserved.
- **Variable pitch reconciles the two.** Continuous *and* turns-only-on-active-levels ⇒ the spiral
  **curls tight to gather at an active level and runs nearly straight through the empty ones.** One
  smooth co-winding curve, bunched where there is something to collect, gliding where there isn't.
- **The knot is a task fingerprint.** So the winding ratio `p:q` is **per-task, not architectural**
  (correcting an earlier guess): `q` = active levels, which changes with the task. Simple task → few
  active levels → small tight knot; hard task → more → bigger knot. This is the **path budget of
  `VOID_LINE_PAPER` restated as a knot** — small for clean two-domain folds, ~2×L for the hard
  three-domain case; "count the confident paths the feature requires." The knot's complexity *is* the
  task's complexity.

### 3.2 The spiral is generated by the points — a derivative-authority ladder
The spiral is **not pre-drawn**; the points build it. Each consensus point is a **steering input**,
and the core is the running sum of the directions they hand it on the way down (the §8 build-up made
literal). Authority over the curve is **ranked by height**, and the rank is a derivative order:

- **The top (coarsest, first) point owns the direction itself — the 1st derivative.** It alone may
  set or reverse the handedness. So the *only* place an unwind-inflection (§3.1) can be planted is at
  the entry, and there is **at most one** per knot. One directional decision, made once, cheaply, at
  the top; everything below is monotone refinement.
- **Each lower point may act only on a higher derivative** (curvature, then torsion). It **bends** the
  path to reach the next point but can never overturn the direction the top locked. Steer, don't
  reverse. The **bottom** point's adjustment is the final landing back onto the origin (the closure,
  π, =1).

This is three structures at once: the **recursion** (`PIXEL_STRAIN`: primary cut sets the frame,
finer cuts live *within* it, robust→fading — coarse commits, fine refines under it); **Taylor**
(`§1.2`: low-order term fixes the trajectory, higher-order terms are bounded, shrinking corrections
that cannot flip it — the residual fade); and the **build-up** (`§8`: the spiral accumulates the
points and reaches down to close). Working analog: **coarse-to-fine / hierarchical decoding** — commit
the coarse structure once, refine details *under* the commitment, never revise the coarse choice.

**Honest cost — error inheritance.** Ranking authority by height means a wrong *top* decision (a bad
primary cut) cannot be undone below — lower points can only adjust *within* it. `PIXEL_STRAIN` states
this: end-to-end recursion on predicted domains "would compound primary error." The top point's cheap
power is also the single point of failure. **Open design fork:** allow a lower point to **escalate** —
detect it cannot reach its next point without fighting the locked direction, and signal *up* to force
the top to re-decide (robust, but breaks the clean one-directional rule and costs a feedback pass), or
forbid escalation (cheap and one-way, but stakes everything on the top being right). A **fat residual
spray near the top** (§4) is exactly the trigger an escalation would watch for. §3.3 softens this by
replacing the single locked direction with a *cone*.

### 3.3 Cones, not vectors — the spiral becomes a solution manifold
Upgrade each point from setting **the** direction to setting a **cone of compatible directions** — a
tolerance, not a value. The cone is native to the math: a half-angle α around the preferred direction
is exactly the set with **cosθ ≥ cos α** (the Born-alignment threshold, §1.1). The point accepts any
direction that aligns with it well enough; `cosθ` is the *threshold the cone enforces*, not a number
it demands.

- **Cone width = resolution.** Coarse level → **wide** cone (fixes only gross direction, lots of
  slack); fine level → **narrow** cone (precise, little slack). Cone half-angle ∝ coarseness ∝
  1/(derivative order). The §3.2 authority ladder is really a **cone-width ladder**, and this
  **dissolves the error-inheritance cost**: the top no longer dictates a value everyone inherits — it
  declares a *wide range*, and lower points genuinely have room to place themselves inside it.
  Disagreement at depth becomes "choosing within the top's wide cone," not "fighting a locked
  direction." The cones *are* the slack §3.2 lacked.
- **One spiral → a space of spirals.** "Pass through the points, stay in their cones" no longer picks
  one curve; it admits a whole **legal set** of valid spirals — the **superposition** (the outer,
  infinite, generated side existing as a *set* before pruning). Jonathan's two operations name the
  two halves: **"lock it in"** = the **Born collapse** to one certified config (§8/§9.1, the
  prune-down to closure =1); **"keep shifting to find all configurations"** = **mapping the manifold**
  from a first feasible seed (the "initial connection") outward.
- **Don't enumerate — measure the dimension.** Listing all configs is intractable (the legal set is a
  continuum). The useful, cheap quantity is the manifold's **dimension = how underdetermined the
  answer is.** 0-dimensional (points + cones pin it to isolated configs) → a **rigid, near-unique
  answer**, high confidence; high-dimensional (loose cones, few points) → **many valid answers**, the
  task is genuinely ambiguous and the manifold's size *is* the ambiguity. This is a **confidence
  readout for free**: tight cones + many points → low-dim → confident; loose → gather more points.
- **Empty intersection = the hard escalation trigger.** If the cones cannot be jointly satisfied by
  any through-curve, there is **no** valid spiral — the top's direction-range was wrong. This
  sharpens §3.2's fork: escalation fires not on a soft "fat spray" but on a hard **contradiction**
  (legal set went empty), which *forces* a top re-decision.

Working analog: **inverse kinematics** — waypoints to hit, joint-angle **cones** as limits, and a
**redundancy manifold** of all poses that reach them; find one solution, then slide along the
manifold (homotopy continuation from a seed).

### 3.4 The circuit — budget is the collapser, and it closes to ground
What picks one config out of the §3.3 manifold? The **budget** — and the answer is already in the
corpus. `FOLDING_CHANNELS`/`SATURATION_BUDGET`: **spend every budget to zero against one fixed,
non-zero reserve — the flow/void budget** (symmorphosis; the void held at ~1/5, banked at the seam).
So the loop locks in the config that **spends down to the void reserve and no further.** The pruner
is the saturation budget, applied to the manifold.

- **The compatibility band is asymmetric (`Shovelcat_29` §10 void economy, V = 1 − U, ε > 0).**
  *Under* the reserve → V > 0, elastic and graceful (safe but wasteful — capacity left on the table);
  *at* the reserve → the symmorphosis target; *over* it → V < 0, the channel **plugs**, the vortex
  **locks**, brittle collapse. So "how far under/over is compatible" is a **slope on the under side
  and a cliff on the over side**: rank toward the reserve, but the hard wall is spending past it.
- **The loop is a circuit, and that is *why* it must close.** Current flows only in a closed loop, and
  the linking number is only defined on a closed curve — so the continuity of §3.1 and the closure of
  §3 are **one fact**: this is a circuit carrying a conserved quantity. **Outer = positive rail**
  (routing out); **inner = negative rail to ground** (returning); **ground = origin = 1**; **the top
  point ties + to −** (also the §3.2 pivot and the §9.3 meet-in-the-middle — one point, three jobs).
- **The conserved budget is `Lk = Tw + Wr`** (`SPHERE_GENERATOR` §B.3, Călugăreanu–White–Fuller — "the
  energy budget for an action"). **Writhe = the outer routing** (the sparse-vesica coil over the top);
  **twist = the inner rotation** (the π-core spinning down). The loop trades routing against rotation
  but cannot make either from nothing; the top point is where writhe converts to twist.
- **Energy is spent on the return (to ground).** Changing `Lk` requires a **cut-and-rejoin** and costs
  energy (topoisomerase spends ATP to do it). **Locking in the answer = setting `Lk` = the irreversible
  step**, and it happens on the negative rail, dissipated to ground. The outbound climb is nearly free
  (reversible superposition, writhe just coiling); the **collapse to one answer is where the energy
  goes** (Landauer, in resonance). Design consequence: **the compute lives on the negative side** —
  generating possibilities (outer) is cheap; *choosing* among them (inner return) is the cost.

**Honest edges.** Exact conservation is the idealization — the `ε` reserve is the slack that keeps the
loop from going brittle, so real loops run *near* conservation with headroom (that headroom *is* the
band). `Lk = Tw + Wr` is literally the ribbon math (not a metaphor); the topoisomerase/Landauer
framing of *energy on return* is a resonance for the cost story, and it only holds because the return
is where the irreversible lock-in sits — never collapse, and nothing is spent (and no answer is
produced).

### 3.5 The weave — the pLM is the medium both rails transit; the void is frictionless
Zoom in on the circuit and the two rails are not separate arcs — they are a **weave through the pLM**,
which sits between them as the medium. Per floor: **origin/LLM core → cross the pLM (inbound
translate) → outer sparse-vesica layer (generate) → cross the pLM again (outbound translate) →
LLM core (gather/store) → up to the next floor.** This is the **loom**: the pLM is the **warp** (fixed
vertical layers), our process is the **shuttle** weaving back and forth, the answer is the cloth. Each
floor is one **bidirectional crossing** — the §1 both-ways permeability, now happening *per level*
instead of once overall. Still sparse: only the active shuttle-pass crosses at each active floor.

- **The positive rail bounces boundary↔inside = the writhe.** The outer rail is not a flat climb; it
  corkscrews between the outer boundary and the inner hole as it rises (the tube-wrapping / poloidal
  component). That in-and-out excursion **is** `Wr`.
- **The coil is generated by the crossings = the twist.** Weaving a strand back and forth through a
  medium *builds* twist (plying, the double helix). So the per-floor pLM crossings are where `Tw`
  comes from. Both halves of `Lk = Tw + Wr` now have a mechanical origin: **writhe from the outer
  bounce, twist from the crossings.** The coils "we had before" are *written by the weaving*, not
  imposed — one half-twist per floor.
- **The zeros are frictionless void, not just absence.** Reading the zeroed sections (§2) as *no
  resistance* turns them into the **void channels** (`FOLDING_CHANNELS`: "the void keeps flowing";
  `Shovelcat_29`: void = uncommitted capacity). So **resistance = commitment**: the current pays only
  where the loop commits (the active gather points — the collapse/energy of §3.4) and **coasts
  frictionless through the void between them.** Sparsity is not merely cheaper — it is the
  *low-resistance path*.
- **Series-waypoint caveat (important).** A true zero-resistance region is a **short** — if the void
  were a *parallel* path, all the current would dump through it and skip the active points, doing no
  work. It only works because the active points are **series waypoints** the loop is forced through
  (exactly the §3.3 must-pass-the-points rule), coasting the void only *between* them. Keep those two
  rules bolted together: drop the mandatory-waypoint condition and the current shorts through the void
  and no answer forms.

Working analog: a **layered transmission line / loom** — a fixed medium (warp) with a shuttle weaving
through it floor by floor, twist accumulating from the crossings, signal coasting the low-loss gaps.

### 3.6 The stitch shape — flat tread out, diagonal riser in, insulated by the void
The unit stitch has a definite shape, and it is a **staircase** (`FOLDING_STAIRCASE`): a **flat tread**
outbound (core → edge, staying low, *not hitting the roof*) plus a **diagonal riser** inbound (edge →
the corner where the next floor meets the core). Tread, riser, tread, riser — climbing floor by floor.
This is the **torus knot unrolled**: wrap the staircase around the hole and it is the §3 knot; slit
the knot and lay it flat and it is the staircase.

- **Asymmetry matches energy-on-return.** Flat out (free, no climb), climb on the return — so all the
  vertical work sits on the inbound leg, exactly §3.4's "energy is spent on the return." The tread
  coasts; the riser crosses the pLM *and* gains a floor.
- **Non-touching = the void reserve wearing a second hat.** The outbound and inbound wires cannot
  touch (that would short — the §3.5 failure). So the outgoing tread must **leave room** (headroom
  under the roof, and a side gap) for the ingoing riser. That clearance **is** the void reserve
  (§3.4/§3.5) — the same ~1/5, now read as **insulation** between the + and − rails. The void does
  double duty: the frictionless conduit *and* the gap that keeps the rails apart.
- **The clearance is what makes it climb.** Forcing a gap forces an **offset**, and that offset *is*
  the pitch to the next floor. Without it the return either touches (shorts, skips the load) or folds
  back on itself (a closed circle, no progress). So the non-touching rule is not just safety — it is
  the generator of the advance. The wires having to dodge each other is *why* the staircase goes up.
- **Failure modes unify.** Over-spend the void budget (§3.4, `V < 0`) → the wires touch → short →
  vortex locks. One failure seen three ways: over-spent budget = wires touching = channel plugged.
- **Cost — clearance caps floor density.** The insulation gap eats vertical room, so it bounds how
  tightly floors (resolution levels) can stack. That ceiling is the **packing budget** (pinned
  ~0.627, `SATURATION_BUDGET`) read as "how many stairs fit given the wire must clear itself."

### 3.7 The Devil's Staircase — the continuous limit, and sparsity taken to measure zero
Zoom the staircase to the limit and it becomes a **Devil's Staircase** (the Cantor function): the
object that reconciles the discrete floors/layers with the continuous current (§3.1). It is **jagged
at every finite zoom yet continuous in the limit** — "keep zooming in and the line became continuous."

- **Sparsity at its extreme.** The **treads** are flat (derivative 0, no work) and in the limit have
  **full measure** — the void, the frictionless coast (§3.5), almost the entire path. The **risers**
  carry the **entire** climb from 0 to **1** (the closure) and sit on a set of **measure zero**. A
  vanishing sliver does 100% of the work: "zero everywhere else" (§2) pushed to the limit. It is a
  **singular-continuous** climb — continuous flow, all increase concentrated on a measure-zero set:
  **resistance = commitment** (§3.5) made exact (coast the void, work in the commitments).
- **Self-similarity = the recursion.** Zoom any riser → the whole staircase returns. That is
  `RECURSIVE_C` (C1, C2, C3…) as *one* self-similar object of infinite depth, not finite levels
  stacked.
- **One scaling ratio = the fade, four voices collapsed.** The staircase has a single number setting
  how riser-height shrinks per finer level — its scaling ratio / fractal dimension. That number **is**
  the fade rate (§4, `PIXEL_STRAIN` 0.84→0.67), which is the cone-width ladder (§3.3), which is the
  step profile (§3.6). Four gradients that looked alike are **one number** read four ways.
- **Truncation is near-lossless (why finite depth is fine).** The true staircase is the infinite-depth
  ideal; we implement a **finite truncation** (floor count capped by §3.6's clearance/packing budget).
  The fade is *why* cutting early costs almost nothing — deep risers carry vanishing contribution.

**Honest edge.** The continuity is the *limit*; the implementation is a finite staircase approximating
it. Singular-continuous means continuous but **not smooth** — the risers are non-differentiable in the
limit, so the "current" does its work non-smoothly, in commitment-bursts (the honest shape of a choice:
a jump made continuous by taking it to the limit).

## 4. The memory — consensus core + sparse residual offsets
How does the return spiral relate to the many line-ends? **Not** by detouring to touch each one
(that regrows the core into a dense web inside the hole — the failure mode). Instead:

- The **rings do the gather.** Many lines land on ring k; the ring's web collapses them to **one
  consensus** at its inner edge (agreement = invariant). The spiral picks up **one point per active
  ring**, not one per line. Division of labor: **rings do many→one (agree); the core does
  level→level→origin (close).**
- The **lines are remembered as offsets from the core.** For each line, store `(layer, distance from
  the spiral, direction)`. The **distance from the spiral is the residual — sinθ, the antimatter,
  the orthogonal part** (§1.1). The spiral is the cosθ (agreement); the offset is the sinθ
  (deviation); `cos²θ + sin²θ = 1` normalizes them per line.

This **rebuilds the Sparse Vesica Expansion as the memory structure:** the spiral is the base term
`f(0)` (the inner shell); each remembered line is a term at its layer d (derivative order) weighted
by its distance (coefficient) → `f(0) + Σ cosθ·v^d`. The torus's memory *is* the equation.

**Working analog — residual quantization.** Keep a coarse base, store the leftover as a residual,
then the leftover of that on the next layer. Distances **shrink with depth** (each layer has less
left to explain) — the same **fade** the pLM recursion already showed (`PIXEL_STRAIN`: 0.84 → 0.67,
gain halving). So the deep turns carry almost nothing and can be truncated.

## 5. Honest bounds
- **Compression is conditional.** The residual ledger is cheap only if the offsets are **few and
  small** — i.e. only if the spiral is a good consensus (same condition as §8.4: does the inner shell
  actually cover the task). If every line sticks far out, the ledger equals the raw data and nothing
  is saved.
- **…but the failure is a signal.** A **fat residual spray at a layer** is a direct readout that the
  consensus failed there — that this layer holds real disagreement the core couldn't absorb. Ledger
  size per layer becomes a live map of where agreement is thin.
- **The return leg must translate back.** For the loop to *close* at =1 and not leak, the pLM's
  output has to re-enter through the skin **in our coordinates** (observer-agreement, a cut, a cosθ
  landing on a branch) — not as a raw contact map dumped on the origin. A one-way skin is two pastes
  facing each other.
- **Error inheritance (§3.2), softened by cones (§3.3).** Because the top point owns the direction,
  its error propagates down; the cone (a *range* rather than a value) gives lower points slack, and an
  empty cone-intersection is the hard trigger to re-decide the top.
- **Enumeration is intractable; measure the manifold dimension instead (§3.3).** The legal set of
  configs is a continuum — its *dimension* (how underdetermined the answer is) is the cheap, useful
  readout, not a full list.
- **Budget conservation is an idealization (§3.4).** The loop runs near-conserved with the `ε` void
  reserve as headroom; the over-spend side is a hard failure (channel plugs), the under-spend side a
  soft waste.
- **Frictionless void needs series waypoints (§3.5).** The zero-resistance reading only holds if the
  active points are compulsory (series); otherwise the current shorts through the void and does no
  work.
- **Clearance caps resolution (§3.6).** The insulation gap between the rails eats vertical room, so
  floor density (how many resolution levels stack) is bounded by the packing budget (~0.627).
- **Continuity is a limit, not smoothness (§3.7).** The Devil's-Staircase continuity is the
  infinite-depth ideal; the implementation is a finite truncation, and even the ideal is
  singular-continuous (non-differentiable at the risers).
- **Status.** This is a construction, not a result. Nothing here is demonstrated end-to-end; the
  demonstrated pieces it rests on are the seam-from-sequence recovery (`CLIMB_WALL`) and the
  web→min-cut recursion that fades with depth (`PIXEL_STRAIN`).

## 6. The test for whether a given skin is real
Does it inject into the pLM's **attention/embedding** space (real integration), or does it only
touch **inputs and outputs** (paste)? Only the first crosses the compatibility gap.

*Artifacts (session diagrams): `folding_skin_geometry.html` (helix + axis, first pass),
`torus_closure.html` (the donut: outer winding over the top, π-core down the hole),
`residual_memory.html` (consensus core + sparse residual offsets fading with depth),
`staircase_weave.html` (the stitch unrolled: flat tread out, diagonal riser in, void-gap insulation),
`devils_staircase.html` (the continuous limit: measure-zero risers carry the whole climb; self-similar zoom).*
