# The Outer Slot — one polymorphic layer (ESM / LLM / Gemini), the combine-by-dissipation mechanism, and why the detector runs it in reverse

*Captures a working-session realization (Jonathan + Claude). The "outer layer" that wraps the
structural inside is **one architectural slot**, and which model fills it is domain-dependent: ESM
for proteins, an LLM for ARC, a vision model (Gemini) for the image detector. Slotting a new element
in is *also* the mechanism by which primitives/domains **combine** — a compatible element dissipates
into the internal flow and merges; an incompatible one persists as a certificate (a seam). The
detector needs the opposite: hold the fills **stable and independent** so the non-dissipating seam
stays legible. Companion to `FOLDING_CLIMB_WALL`, `FOLDING_ONTO_PLM`, `FOLDING_SKIN`,
`FOLDING_OBSERVERS`, `SPHERE_GENERATOR`, `SPARSE_VESICA_EXPANSION` §18.19, `SHOVELCAT_CHECKER_V6`,
`FOLDING_VOID_LINE_DRAW`. Status: framework synthesis; the load-bearing pieces are tested (tagged
below), the unification and the combine/detect duality are design-stage.*

---

## Part I — The outer layer is one polymorphic slot

The framework's central move past the wall is *"wrap the structural inside with a learned outer
layer"* (`VOID_LINE_PAPER` §11, `FOLDING_CLIMB_WALL`). It is stated there for two domains and it is
the *same slot* both times:

- **ARC:** structure-only genome (inside) → wrap with an **LLM** (outer layer) → sparse-vesica model.
- **Protein:** void-line geometry (inside) → wrap with **ESM** / a pLM (outer layer) → seam from
  sequence (DEMONSTRATED: seam recovered from sequence at 82–94%, `FOLDING_CLIMB_WALL`).

The **AI detector is the third instance:** the void-line / seam-committee geometry (inside) → wrap
with a **vision foundation model, Gemini** (outer layer) → seam / disagreement map on an image. So
Jonathan's question — *"aren't we putting Gemini in the same place as the pLM?"* — is exactly right.
Gemini is not one model in a pipeline; it is the **current occupant of the outer-layer slot**, the
same role ESM plays for folding. One architecture (inside geometry + outer-model slot + a membrane
between), three fillings.

**The slot accepts other things, and the committee is how you combine several fills.** Both halves of
Jonathan's guess hold:

- *Polymorphic.* The inside is model-agnostic — it emits a **relational** object (observers = pairwise
  agreements, the committee = consensus over a web, `FOLDING_SKIN` §1). Any pretrained model with an
  internal relational structure can fill the slot: ESM's attention web, an LLM's, a VLM's.
- *Combined by agreement.* `FOLDING_ONTO_PLM` (TESTED): **observers = attention heads**; no single head
  is the truth (50–95%), but the **blind committee** (mean of all 240 heads) recovers the invariant at
  89–94%. So multiple models in the slot = **multiple observers**, combined by agreement — the same
  committee, one level up (models instead of heads).

**Design note (from `FOLDING_SKIN` §1): read the slot relationally, not per-region.** *"The seam is in
the attention, not the embeddings"* — per-residue/per-region reads sit at chance (52–62%); the
relational web carries the seam (~90%). For the detector this means: don't just ask each model "is this
region fake?" (a per-region, embedding-like read). Read how the regions **relate** — which cohere with
which — because the disagreement between those relations *is* the seam.

---

## Part II — Slotting in *is* the combining mechanism (dissipate-if-compatible)

Jonathan: *"that's probably the link to how proteins or our ARC primitives start combining — once it
slots in, the flows inside dissipate the new element, if it's compatible."* This is the growth rule the
corpus already carries, stated from the algebra side:

- **Compatible → dissipates → merges.** A new element that aligns with the existing structure is
  **absorbed** — it becomes part of the flow and stops being a distinct thing. `SPHERE_GENERATOR_TEST`
  (Test 3, TESTED): drops **parallel to an existing direction merge — "absorbed = redundant."** That is
  the dissipation: the new element's residual goes to zero, it closes into what's already there
  (`FOLDING_SKIN` §4: the residual is the un-absorbed part; a compatible element leaves ~none). This is
  **how primitives/domains combine** — ARC compounds-of-compounds ("molecules," `INNER_SHELL`), a fused
  protein domain, a Fano lateral merge.
- **Incompatible → persists → certificate.** An element that *cannot* be dissipated is a **zero divisor**
  — `a·b = 0`, a proof that no product of existing primitives reaches it (`SPHERE_GENERATOR` E.2). It does
  **not** merge; it stands up as a **void line / seam**, and it either **mints a new primitive** (ascend)
  or is **anchored** as a marked hole. TESTED backbone: 0 zero divisors below sedenions, 84 at the
  sedenion shell (`SPHERE_GENERATOR_TEST` A) — the wall where dissipation stops being possible.
- **The compatibility test is closure / θ / the cone.** "Compatible" = aligns within tolerance:
  `cosθ ≥ cos α` (the Born-alignment cone, `FOLDING_SKIN` §3.3), θ→1 = the interface matches on all axes
  (`SPARSE_VESICA` §18.11). Inside the cone → dissipate and merge; outside → the seam.

So the slot is a **growth engine with two outputs**: compatible elements dissipate in (structure
*combines*); incompatible ones certify a gap (structure *mints*). Proteins and ARC primitives "start
combining" via the first route.

---

## Part III — Stability = convergence of independent routes (the detector runs the slot in reverse)

Jonathan's key qualifier: *"but here we need them stable."* For **combining** you *want* dissipation
(absorb, merge). For **detection** you must prevent it — and the corpus already measured what
"stable vs. dissipated" means, in `SPARSE_VESICA` §18.19 (TESTED, full 400-eval):

- A per-task synthesis is an **ephemeral synthetic isotope** — it "does not need to be general, only to
  hold together for **one measurement** (θ=1 verification = **the detector**)." Most decay.
- The **island of stability = the mint detector**: an element is *stable* (a real, keepable "floor
  atom") when **independent routes re-synthesize it identically**. MEASURED: survival = **convergence** —
  the one surviving task had two independent routes land on the *same* map; every decayed task supported
  *many distinct* maps. **Acceptance rule: trust a synthesis only when the distinct-route count is 1
  (routes converge)** — on that sample, 1/1 precision, all decays rejected.

Read into the detector, this is the whole principle:

- **Authentic = a stable floor atom.** Independent observers (the models in the slot, read relationally)
  **converge** on the same reading of a region — it coheres from every route, θ=1, nothing left over.
  Stability *is* committee agreement (`FOLDING_OBSERVERS`: agreement = the invariant).
- **Fake = an ephemeral isotope.** A generated region **holds together for one glance** (the surface, a
  single forward pass) but **decays under independent multi-route scrutiny** — the observers diverge, the
  routes give many distinct readings. That divergence is the **seam** (`FOLDING_SKIN_DETECTOR` Test 5:
  the committee disagrees 2.1× at the seam). AI images are, in this exact sense, synthetic superheavy
  elements: stable enough to pass one measurement, not stable across independent re-derivation.

**Therefore "we need them stable" is a hard design constraint, not a preference.** The signal is
*convergence of independent routes*, so the routes must **stay independent** — if the models in the slot
dissipate into each other (or a single model smooths the anomaly into coherence), you manufacture
agreement and lose the seam. Combine mode: let compatible elements dissipate and merge. Detect mode:
hold the fills stable and independent so the non-dissipating seam stays legible. **Same slot, opposite
operating mode.** (This is why the tested caution matters — `FOLDING_ONTO_PLM`: no *single* head/model is
the truth; only the independent committee recovers the invariant. A lone model in the slot both fails to
converge-check *and* is free to dissipate the anomaly.)

---

## Part IV — Concretely, for v6

- **One fixed roster in the outer-layer slot** (Jonathan's "commit to one setup"): Gemini prominent (for
  the XPrize and because it fills the pLM slot cleanly), plus at least one independent partner (Claude),
  read **relationally**. Drop v5's degrade/customize machinery — the committee *needs* a fixed, genuinely
  independent set, not an optional one.
- **The acceptance rule is the §18.19 convergence test.** A region is authentic when the independent
  routes **converge** (distinct-route count → 1, θ=1); it is flagged (seam) when they **diverge**. This is
  the v6 agreement/disagreement map, now with a stability/half-life reading: authentic = stable atom,
  fake = decaying isotope.
- **A DIRE-style reconstruction-error score is another route into the slot** — pass the image through a
  diffusion model and measure the residual; on-manifold (low residual) vs off-manifold is the same
  stability question from a different observer. It composes with the committee as one more independent
  route (more convergence evidence), not a replacement.
- **The folder/ARC use the same slot in combine mode** — compatible primitives/domains dissipate and
  merge (grow the program/fold); the detector holds them apart. One architecture, two operating modes.

---

## Part V — Vibration: the stochastic way to generate the independent routes

A diffusion model is **thermalize-then-anneal**: crank the image to pure noise, then cool it step by
step while a learned denoiser pulls each sample toward the data manifold. The cleanest picture is a
**Chladni plate** — vibrate it and sand sorts itself onto the nodal lines (the zeros = the void
lines). Jonathan's *"vibrate our void lines and see how things sort"* is a good picture of generation,
and it maps onto knobs we already have:

- **Noise level = the thickness-by-level knob** (`FOLDING_VOID_LINE_DRAW`). High noise fixes coarse
  global structure (thick void lines); low noise fixes fine detail (thin lines). The diffusion schedule
  *is* the devil's-staircase zoom run generatively.
- **Each denoise step = a closure pull** toward θ=1 / on-manifold; the **randomness is the ψ/chaos
  side** — it samples *one* config from the manifold-set rather than collapsing to the nearest (the
  `FOLDING_SKIN` §3.3 "keep shifting to find all configurations" vs "lock it in").

**Why it matters for the detector — vibration manufactures the independent routes the stability test
(Part III) needs.** Perturb the image, let the process re-anneal, and measure how far it moved:
authentic content is *off*-manifold and does **not** settle back (high reconstruction error, seams
re-crystallize differently each shake → the region is unstable → flagged); generated content is already
*on*-manifold and sorts right back (low error, converges) — this is the DIRE reconstruction signal and
the §18.19 convergence test in one. The point: instead of needing N separate models as the independent
routes, you can use **N noise perturbations of one process** — cheaper. The deterministic
grid-relaxation gives *one* settling; vibration turns it into a *distribution* of settlings, which is
where the confidence/half-life number comes from. It is an **add-on observer** (running a diffusion
model is heavier than the committee), not the core, and the mapping is **structural** (thermalize–
anneal, coarse-to-fine, manifold-pull), not a literal identity.

## Honest ledger

**TESTED**
- Observers = attention heads; blind committee recovers the invariant 89–94%, no single head is the
  truth; seam in attention, not embeddings (`FOLDING_ONTO_PLM`).
- Seam-from-sequence via the pLM outer layer, 82–94% (`FOLDING_CLIMB_WALL`).
- Absorbed = redundant (parallel drops merge); unique = certified-independent but not automatically
  useful (`SPHERE_GENERATOR_TEST` Test 3).
- 0 zero divisors below sedenions, 84 at sedenions — the dissipation wall (`SPHERE_GENERATOR_TEST` A).
- Survival = convergence of independent routes; accept only when distinct-route count = 1 — measured on
  the 400-eval (`SPARSE_VESICA` §18.19). "θ=1 verification = the detector."
- Committee disagrees ~2.1× at the seam (`FOLDING_SKIN_DETECTOR` Test 5).

**FRAMEWORK / DESIGN-STAGE**
- The outer layer as a single *polymorphic slot* across proteins/ARC/images (a clean unification of
  three tested instances, but not itself a measured claim).
- "Dissipation" as the α / information-overflow reading (`Shovelcat_Theory_10`) — framework substrate.
- The detector-as-island-of-stability mapping (authentic = stable atom, fake = ephemeral isotope):
  coherent and built on tested pieces, **not yet run on images** — this is the first thing to benchmark
  (GenImage / DFBench), isolating the convergence rule before adding zoom or reconstruction cost.
- The combine-vs-detect "opposite operating mode" is a design principle, not a measured image result.

*Sources: `FOLDING_CLIMB_WALL` / `VOID_LINE_PAPER` §11 (wrap-the-inside, the outer layer), `FOLDING_ONTO_PLM`
(observers = heads; blind committee; seam in attention), `FOLDING_SKIN` §1/§3.3/§4 (relational membrane;
the cone; residual absorption), `SPHERE_GENERATOR` E.2/C.2 & `SPHERE_GENERATOR_TEST` A/Test 3 (zero-divisor
certificate; absorbed=redundant; sedenion wall), `SPARSE_VESICA_EXPANSION` §18.11/§18.19 (θ=1 alignment;
isotope half-life; survival=convergence; distinct-route-count=1 acceptance), `FOLDING_OBSERVERS`
(agreement=invariant), `FOLDING_SKIN_DETECTOR` Test 5 (disagreement=seam), `SHOVELCAT_CHECKER_V6` (the v6
spec), `FOLDING_VOID_LINE_DRAW` (the void line as draw/segment primitive). External: DIRE reconstruction-error
detection (Wang et al., ICCV 2023) and successors.*
