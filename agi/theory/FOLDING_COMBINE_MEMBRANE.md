# Combining as Generation — the residue, the carried rules, and the membrane that decides

*Captures a working session (Jonathan + Claude). Linked moves, then measured runs. First: the detector's
"window from outside that's inside our space" is the same operation as how proteins/elements/ARC
primitives **combine** — slide a new element in, let it dissolve and expand the primitive, and the part
that can't be absorbed leaves a **residue**. Second: combining is not free — each primitive drags along
**rules that must follow**; those carried rules are the **membrane**; the **residue is where a carried
rule is violated.** Third (dynamics): the membrane is **reactive**; dissolve the *old* wall only where a
rule is **currently failing**; the boundary re-forms **further out**; the old rule survives as a **fluid
field**. VI: dissolving object rigidity, measured. VII: dissolution **non-unique**, minimal-heat = **rigid
fragments**, dissolved state **decays unless driven**. VIII: the wall is **non-uniform** — break **only the
segment you want**; value is in **residue SELECTION**. IX (energy axis): **ATP** = the missing second wall
(**fixed point + currency**); the ARC **goal image is that ATP**; hard crossings are **basin switches**
(Green–Tao), handles = residue/zero-divisors. X (run): void line = **trace of sliding void points as basins
merge**; a Voronoi/watershed generator ran **0 exact — negative** (ARC basins are connectivity/periodic/
mirror, not distance). XI (run): each task is **its own window, chained across space** — connect **through
intermediates**; a spanning-chain got **2 INK_ADDED exact vs Voronoi's 0**. XII (run + frame): the
**union synthesizer** (chain + connectivity + periodic + mirror + distance) built and run — **routes each
task to its correct basin-geometry, 5 solves, 0 regressions** (recovers `a5313dff` that gravity shattered),
but **0 net-new** — the pure-structure floor; the next lever is the **outer pLM/LLM layer**, inside-first.
Companion to `FOLDING_OUTER_SLOT`, `FOLDING_CLIMB_WALL`, `INNER_SHELL`, `SPARSE_VESICA_EXPANSION`,
`SPHERE_GENERATOR`, `FOLDING_ATP_REFERENCE`, `FOLDING_TWO_WALLS`, `FOLDING_VOID_LINE_DRAW`, `RESULTS.md`.
Status: **VI–VIII, X, XI, XII measured — all 0 net-new; the pure-structure inside WORKS (routes by
geometry, no regressions) but is at its floor; the outer layer is the next lever (Phase 2).***

---

## Part I — Combining is the one operation that GENERATES

The measured wall on ARC is not a missing operator — it's a missing *capability class*. `RESULTS.md`
Brick 12: *"we built a TRANSFORMER, not a GENERATOR."* Every inner-shell primitive selects / moves /
recolours / crops **existing** content. The lowest solve-rate by far is **INK_ADDED — tasks that create
new content — 6%**, vs MOVED at 36%. `INNER_SHELL` flags the generation family as "thinnest — the open
frontier."

Combining is different in kind, and that's the point: **slide element B into primitive A, let it
dissolve, and the result A′ is strictly bigger than A.** It has cells A never had. That is ink added
without a dedicated draw primitive. The building phase (`INNER_SHELL`, 62 primitives → 73/400) made the
elements; combining them is the first shell operation that *manufactures* structure instead of
rearranging it. Combining has two products:

- **the absorbed part** dissolves into the flow and **expands the primitive** → clean growth (the INK).
- **the residue** — the part that can't dissipate — is the **exception**, routed three ways the corpus
  already names (`FOLDING_OUTER_SLOT` Part II): **mint** it as a new primitive (ascend), **anchor** it
  as a marked hole, or read it as a **certificate** that these two shouldn't combine (the seam).

This restates and sharpens `FOLDING_OUTER_SLOT`: compatible → dissipates → merges; incompatible → zero
divisor / seam. What's new is treating the **residue as the product on the combine side**, not merely
the alarm on the detect side — and identifying it as a candidate mechanism for the INK_ADDED gap.

---

## Part II — Combining carries rules: the membrane

The operational key. **A primitive is not just an operation — it is an operation plus the constraints
it obligates.** Combine two and you inherit the *union* of their obligations. "Move" contributes
displacement; "objects" contributes *solid, occupies cells, has a boundary*. Put them together and the
collision rule **follows automatically** — you cannot have solid objects and free displacement without
one, or the objects stop being solid. That carried boundary is the **membrane**.

**The shell already proves this.** The motor role has no bare `move`. It has `shift` (dumb, no rules) and
then `gravity(dir)`, `gravityObj(dir)`, `moveContact(dir)` — each of which **bakes the wall rule in**.
"Move until contact" *is* "move, but not into walls" compiled into one primitive. And the MOVED class has
the **highest solve-rate in the whole project (36%)** — the place where the carried constraint is built
in is the place that works best. Viability = carrying the rules along.

**Two modes of membrane — the solid/fluid split, both already in the theory:**

- **Solid / hard stop** — the wall. `moveContact` halts at it. Shovelcat's **ϕ-constraint**.
- **Fluid / redirect** — `Shovelcat_Theory_11_3` §5.4: *"Constraint does not merely prohibit; it
  redirects… the collision between the two domains creates curvature."* The wall bends the move.

---

## Part III — The residue IS the constraint violation (moves one and two click together)

Part I: combining leaves residue where a part can't be absorbed. Part II names **why** — **it violates a
carried rule.** An object shoved into a wall is residue *because* it broke the boundary constraint that
came with "objects." So the membrane is the **compatibility test made local** (general form: the cone / θ,
`FOLDING_SKIN` §3.3): carried structure intact → the element dissolves; a rule breached → that part
crystallizes as residue. **The residue = the constraint violation made visible** — and a **constraint-
discovery signal**: watch where residue piles up, it names the rule you failed to include.

---

## Part IV — Viability tests already in the corpus (tested hooks)

- **Balancing filter (`SPARSE_VESICA` §18.5).** Colour-histogram conservation as a cheap gate; reaction-
  network (§18.4): each combination is `(input) --[ops]--> (output)`.
- **θ = 1 (`INNER_SHELL` u11).** θ = |changed| / |truly changed|; all 10 solves θ=1.00, overfit 0.56.
- **Convergence guard (`SPARSE_VESICA` §18.19).** Keep a minted residue only when independent routes
  converge (distinct-route count → 1).

---

## Part V — The membrane reacts: failure-targeted dissolution and the forced-outward climb

The membrane reacts — **the new element dissolves the OLD wall.** Two conditions: **compatible with the
body** yet **reactive against the blocking wall.** **Trigger:** combine only where a rule is *currently
failing* — the task names the wall (`RESULTS.md` Brick 11; swarm UCB + FailureBuffer). **Growth is forced
outward:** the inner shell is certified (`SPARSE_VESICA` §9.2), so the new boundary re-forms *further out*
— the **shell climb** (sedenion seam 0→84 zero-divisors, circle→helix lift, void₀→void₁→void₂).
**Absorb, not delete:** the dissolved wall becomes a **passable fluid gradient**; validity = θ=1 on old
*and* new (§18.19).

---

## Part VI — Dissolving object rigidity (measured, 400 tasks)

Reimplemented `moveToContact`; its wall carries grid-edge + object-collision + **rigid-body** rules.
Standalone solves **0/400** (composition-only). Dissolving rigidity → **cell-gravity solves 2**
(`1e0a9b12`,`3906de3d`, test-generalizing) vs rigid's 0 — **but both already project-solved, 0 net-new**
(convergence, §18.19). Rigidity is **load-bearing**: rigid beats cell by +0.13…+0.23 on ~12 tasks;
cell-gravity **shatters** intact shapes (`a5313dff`,`6d0160f0`). θ=1 **add-alongside = strict superset**
(+2, 0 regression): absorb-not-delete confirmed necessary. *(`arc_move/grav/reg/final.py`.)*

---

## Part VII — Non-unique dissolution: temperature ladder + sustaining cost

Temperature = shatter granularity. T0 whole 0, T1 colour 1, T3 cols 2, T4 cell 2. **Minimal heat is
task-specific and usually NOT full melt** (`1e0a9b12` at T1 = rigid colour-fragments). 0 net-new; no
temperature solves the 12 regression tasks (need rotation, or aren't gravity). **The dissolved state is an
EXCITED state that decays unless driven** (isotope half-life §18.19; "expend effort to maintain,"
`Theory_11_3` §12.5): self-sustaining (new stable atom) vs driven (ongoing budget cost). *(`arc_frag.py`.)*

---

## Part VIII — The wall is non-uniform: selection is the whole game

Non-uniformity is a **tested seam property** (`FOLDING_WINDOW_SEAM`; `FOLDING_SKIN_DETECTOR` Test 5). The
residue names *which segment*. **Run:** untargeted "deposition gravity" (break at every contact)
degenerates to melt (0.509 ≈ cell 0.504, ≪ rigid 0.673) — **refuted** the preserve-rigidity prediction.
**Value is in SELECTION** — break only the segment the residue points at. *(`arc_local.py`.)*

---

## Part IX — The energy axis: ATP as fixed point + currency, the goal, the basin switch

`FOLDING_TWO_WALLS` (tested): two walls — **carbon (structure) + ATP/phosphate (energy)**; Parts I–VIII are
all structure, ATP is the **energy axis** (the maintained force of VII); the **effort budget IS the ATP
pool**. **The ARC goal image IS the ATP** — F1-ATPase's fixed pivot with windows driven around it; the
train output anchors (fixed point) and drives (dissolve toward it) — *the driver VIII lacked.* **Wall-break
= basin switch** — Green–Tao t₃(11)=16 unreachable on a field (no zero-divisor handles); the residue **is**
the zero-divisor handle into an isolated basin; barrier height = ATP/budget cost. **Spec:** goal = fixed
point + driver; residue = rule + segment + handle; cost = budget. Runnable, not yet run.

---

## Part X — Void line as basin-merge trace (run: negative for Voronoi, refined)

Basin merge = watershed; the saddle sweeps the line — **combining basins draws lines**, closing the thread
to the Part I gap. Hoped form-free where the form-locked synths score +0 eval (`stamp2` +9/+0, `trace`
+1/+0). **Run — 0/400 exact.** Corrected for the sparse-output artifact, lift on **18 tasks, ~all
INK_ADDED** (engages the generation class), but the near-misses are **periodic** (`caa06a1f`),
**connectivity** (`9edfc990`), **mirror** (`11852cab`) — not distance. **ARC generation basins are
connectivity/periodic/mirror, not Voronoi.** *(`arc_voronoi.py`.)*

---

## Part XI — Each task its own window, chained: connect through intermediates (run)

F1-ATPase is a **star** (windows around one ATP); ARC is **not** — each task-window has its **own** goal/ATP
and they **chain neighbor-to-neighbor**. A global merge skips intermediates (diagnoses X). Grounding:
waypoint-snapping (`SPHERE_GENERATOR` C.5), incidence network (`SPARSE_VESICA` §27), weak reuse 0→8%
(`RESULTS.md`). **Run:** a **minimum-spanning-tree chain** over anchors got **2 INK_ADDED exact**
(`1f876c06`,`40853293`) **vs Voronoi's 0** — connect-through-intermediates > global merge, confirmed. 0
net-new. *(`arc_chain.py`.)*

---

## Part XII — The union synthesizer built (run) + the strategic frame (fold the path, then the layers)

Jonathan: *"we still have to wrap a path to the answer — fold our way to it. There's still the stuff between
the webs. We haven't done a pLM layer or multiple layers, and we won't get much until we do — but this part
needs to work first."*

**Run — the unified inside WORKS: routes by geometry, 0 regressions** (`arc_union.py`). One θ-gated
synthesizer = the **chain backbone (XI)** + the **union of fill-geometries (X-refined)**: connectivity
(flood-fill), periodic (tile), mirror (symmetry), distance (Voronoi). Each task routed to whichever form
hits θ=1 (train+test):

| form | geometry | solves |
|---|---|---|
| chain | connect-through-intermediates | 2 — `1f876c06`,`40853293` |
| flood | connectivity basin | 2 — `00d62c1b`, **`a5313dff`** |
| mirror | symmetry basin | 1 — `496994bd` |
| periodic / voronoi | tile / distance | 0 |
| **UNION** | | **5, 0 regressions** |

- **The routing is the point.** The θ-gate selects the correct basin-geometry per task and **regresses
  nothing** — notably **`a5313dff`, which cell-gravity shattered in Part VI, is now solved exactly by
  flood.** The residue diagnosis (X) held: it was never gravity, it's a connectivity basin, and the union
  puts it in the right bucket. This is "this part working": a correct, non-breaking, multi-geometry router.
- **But 0 net-new, and depth-2 compositions add nothing (0 new).** All 5 are already project-solved via the
  certified fillHoles/symmetry/connect ops. So the inside can be made *correct and non-regressing*, but its
  coverage is capped — the **pure-structure floor**, now confirmed from the synthesizer side too, matching
  every other route in `RESULTS.md`.

**The strategic frame (Jonathan's, corpus-backed).** *Fold the path, don't draw it:* the answer is a
**folded** reaction network — forward bounce + retro-from-goal meeting in the middle (`SPARSE_VESICA`
§18.3/§18.6), the chain threading the webs (XI) through the stuff between them (the fill-union, X), wrapping
toward the goal/ATP (IX). *The pure-structure path is at its floor* — six mechanisms, 0 net-new; `RESULTS.md`
already concluded pure structure tops out ~14–18% and gains need the deferred outer-model lever. *The next
lever is the outer layer* — `FOLDING_OUTER_SLOT` / `FOLDING_CLIMB_WALL`: wrap the structural inside with a
learned model (pLM seam-from-sequence **82–94%**, the one move that crossed the wall; LLM/VLM for ARC),
then **multiple layers** = multiple observers combined by agreement (`FOLDING_ONTO_PLM` blind committee
89–94%). *Inside-first is the correct order:* the outer layer **wraps** the inside — it amplifies a working
relational substrate (`FOLDING_SKIN` §1, read relationally), it cannot rescue a broken one. **Phase 1
(this session): the union inside works — routes by geometry, 0 regressions, at the floor.** **Phase 2 (next):
wrap it with a pLM, then stack layers — where the gains are.** *(`arc_union.py`.)*

---

## Honest ledger

**MEASURED (this session, all 400 ARC-1 training tasks — every result 0 net-new)**
- Standalone `moveToContact` 0/400 (composition-only); residue-localizes-the-wall only under the
  conservation filter (25/400).
- Cell-gravity → 2 test-generalizing (convergent); rigidity load-bearing (+0.13…+0.23, ~12 tasks); θ=1
  add-alongside = strict superset (+2, 0 regression).
- Temperature ladder: minimal heat task-specific; no regression task solved.
- Untargeted segment break ≈ melt (refuted preserve-rigidity); value is in selection.
- Voronoi/watershed 0 exact; lift on 18 INK_ADDED tasks but they're periodic/connectivity/mirror not
  distance (hypothesis refined).
- Chain-connect 2 INK_ADDED exact vs Voronoi 0 (connect-through-intermediates confirmed).
- **Union synthesizer: 5 solves (chain 2 + flood 2 + mirror 1), routes by geometry, 0 regressions,
  recovers `a5313dff`; depth-2 comps +0; 0 net-new — the pure-structure floor from the synthesizer side.**

**TESTED (prior corpus)**
- MOVED 36% vs INK_ADDED 6%; balancing/reaction/θ/convergence; seam non-uniform; shell climb 0→84;
  ATP-reference & two-walls (energy axis); Green–Tao basin needs zero-divisor handles; waypoint-snapping
  (C.5); incidence network (§27); weak reuse 0→8%; `drawBox` 51→56% & dissolve 8/8; form-locked synths
  `stamp2` +9/+0, `trace` +1/+0.
- **Outer layer as the wall-crosser:** seam-from-sequence **82–94%** via the pLM slot
  (`FOLDING_CLIMB_WALL`); blind committee 89–94% (`FOLDING_ONTO_PLM`) = "multiple layers."
- **Pure structure tops out ~14–18%; bigger gains need the outer-model lever** (`RESULTS.md`).

**FRAMEWORK / DESIGN-STAGE — the plan**
- **Phase 1 (done, at floor):** the chained, multi-basin, goal-driven union synthesizer works as a correct
  non-regressing router (XII). Remaining inside builds: residue-selected segment-local dissolution
  (VIII–IX, goal/ATP-driven — not run); fragment rotation; self-sustaining-vs-driven (needs composition).
- **Phase 2 (the lever):** wrap the working inside with a **pLM/LLM outer layer**, then **stack layers**
  (`FOLDING_OUTER_SLOT`/`CLIMB_WALL`/`ONTO_PLM`). Inside-first; the layer amplifies, it can't rescue.

*Sources: `src/ops-move.ts`/`objects.ts`/`theta.ts`/`verify.ts` (reimplemented), `FOLDING_OUTER_SLOT`,
`FOLDING_CLIMB_WALL`, `FOLDING_ONTO_PLM`, `INNER_SHELL`, `RESULTS.md`, `FOLDING_ATP_REFERENCE`,
`FOLDING_TWO_WALLS`, `FOLDING_VOID_LINE_DRAW`, `FOLDING_PIXEL_TRANSMISSION`, `GEN_DRAW_RESULTS`,
`TRACE_RESULTS`, `TRUST_AUDIT_RESULTS`, `FOLDING_EFFORT_BUDGET`, `FOLDING_WINDOW_SEAM`,
`FOLDING_SKIN_DETECTOR` Test 5, `SPHERE_GENERATOR` C.5 & Part D / `ORCHARD_16_FINDINGS`,
`SPARSE_VESICA_EXPANSION` §9.2/§10/§18/§27, `SPHERE_GENERATOR_TEST` A, `FOLDING_SKIN` §1/§3.3,
`Shovelcat_Theory_11_3` §5/§12. Artifacts: `arc_move.py`, `arc_grav.py`, `arc_reg.py`, `arc_final.py`,
`arc_frag.py`, `arc_local.py`, `arc_voronoi.py`, `arc_chain.py`, `arc_union.py`.*
