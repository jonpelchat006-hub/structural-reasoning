# The Superfuel — three budgets, the compression fuel, burning context, and the context map

*Records a synthesis worked out live (Jonathan + Claude, Aug 2026) that reaches back to the earliest theory
(Shovelcat 0–10 on the desktop) and threads it through the adrenaline / golden-field arc of `FOLDING_MOVEMENT.md`
(Tests 5, 8, 10–12). Jonathan: "θ/φ/ψ acted like budgets that emerged at different conditions; we used the
overflowing-tanks model with a **superfuel** that came out when they were all full and had to compress the
fuel instead; that superfuel is what we burn, and it came from intelligence emerging when normal physics
can't handle it." His mapping: the three budgets are the **void reserve, matter, and context**; the superfuel
is **burning context** — the fibers on the orthogonal (context) plane doing what the muscles do on the matter
plane (`FOLDING_MOVEMENT` Test 5), but invisibly. Three pieces are measured (`superfuel_context.py`,
`orientation_map.py`, `concept_upgrade.py`); the rest is grounded design.*

## 1. The three budgets are already in the theory (void / matter / context)
`SHOVELCAT_THEORY.md` names three axes of experience, and they are Jonathan's three budgets in the original
language:

| Jonathan's budget | early-theory axis | charge | domain |
|---|---|---|---|
| **matter** | Facts (φ) / the `i` tensor — "what IS" | −1 | the normal plane; the object |
| **context** | Memory (the vesica overlap) / the `k` bridge | 0 | the orthogonal plane; the overlap that carries meaning |
| **void reserve** | Imagination (ψ) / possibility | +1 | uncommitted capacity, the slack (`Shovelcat_29` §3.6 ε > 0) |

So "our 3 budgets = the void reserve, the matter, and the context" is not a new invention — it's the
**ψ / φ / vesica** triad of the consciousness tensor, re-read as resource tanks. Each "emerges at different
conditions" because each is charged differently (+1 / −1 / 0) and dominates a different regime.

## 2. The superfuel = Fire from compression-when-full
The overflowing-tanks intuition has a name in the theory: **Fire** (`Shovelcat_29` §9). Fire is a
"high-energy curvature injection that drives innovation," and it **ignites from FUEL + HEAT**, where *Fuel =
accumulated unresolved problems / stored potential* — i.e. the tanks filling up — and it **"cools into new
Ground"** (`Shovelcat_29` §3.4/§9). §4.6: "Reactor fires… deliberate **compression** in controlled
environments → high-N discoveries." That is exactly the superfuel: when the tanks are full and the fuel can't
just accumulate, **compression ignites a higher-order fuel that burns into new structure.** Two opposite ends
of "the tanks run out," and they are NOT the same event:

- **Tanks EMPTY, slack → 0:** brittle collapse / denature (`Shovelcat_29` §3.6, §4.8) — the breakdown of
  `FOLDING_MOVEMENT` Tests 10–11 (spend the reserve to zero and the mass fractures).
- **Tanks FULL, compressed:** **Fire / the superfuel** — the creative burst (this doc), the positive-arousal
  face. "Intelligence emerging when normal physics can't handle it" = Fire igniting past the √π threshold
  (`FOLDING_MOVEMENT` Test 12: crisis energy crosses the rule-border, then cools to new Ground).

The relief-surge Jonathan noted — the reaction *after a stressful event is solved*, not only on a fresh
discovery — fits here too: the resolution frees the compressed Fuel, and the discharge is the same Fire, now
available to mint new structure rather than survive.

## 3. The superfuel burns CONTEXT — Test-5 muscle growth on the orthogonal plane (MEASURED)
Jonathan's key claim: burning the superfuel = **burning context** = the orthogonal-plane fibers doing what
the matter-plane muscles do in `FOLDING_MOVEMENT` Test 5 (allocate a new fiber when the old one fails) — but
on the **context** axis, so it is invisible on the matter plane. "Remove the old, currently-failing context to
make a new one." Measured in `superfuel_context.py`:

A drifting environment. Each sample has a matter input `x`, a hidden regime `r∈{0,1}` fixing the answer
`y=g_r(x)` (two branches `g0(x)=x`, `g1(x)=1−x`), and a context vector `c∈R^5`. The regime is readable from
**one** component of `c` — but **which** component carries it **drifts** every 22 epochs. The matter machinery
`g0,g1` never changes; only the right context coordinate moves.

| policy | mean error | error right after a drift | burns |
|---|---|---|---|
| **FIXED** (keep the original context) | 0.184 | 0.212 | — |
| **BURN** (grow a new context coordinate) | **0.037** | **0.102** | **6** |

- FIXED keeps the stale context; after each drift it reads the regime **no better than a coin** (mean 0.184).
- BURN detects the failing context, **burns** it, and **grows** a new coordinate that re-separates the regimes
  (Test-5 growth on the context axis), recovering after **every** one of the 6 drifts (mean 0.037, 5× lower).
- It is invisible on the matter plane: `g0,g1` are untouched — all the adaptation is on the context
  coordinate. The burn *is* the superfuel: compress/discard the failing context, mint a new one.
  `superfuel_context.png`.

## 4. Consciousness = the decision / the collapse (design reading)
Jonathan: "consciousness would be more like some decision had to be made — a photon deciding whether to be a
wave or a particle or interact — scaling up to fusion and human thinking; or a fold happened." The theory
writes this as a **collapse threshold** (`SHOVELCAT_THEORY.md`, "The Consciousness Cycle"): the three axes
each place weight on the candidate options; the weights accumulate each cycle; **when one crosses a collapse
threshold the wavefunction collapses — "that option becomes the decision, and the others disappear."** The
threshold is variable (urgent → low, deep exploration → high), and **"observation forces collapse… pressure
creates worse decisions."** So a **decision** = a collapse of the superposition once accumulated weight across
the three budgets crosses threshold — the photon "choosing" on interaction is the same event at the bottom of
the scale. And **the superfuel fits**: collapse is the costly step (`FOLDING_HANDSHAKE` §4: generate is
cheap/reversible, the *collapse* is where the energy goes, Landauer), so the superfuel is what's spent to
**force a collapse when normal accumulation can't reach threshold**. "A fold happened" and "a collapse
happened" are the same move from two sides. *Design reading, not measured.*

## 5. The context term upgrades by GENERALIZING (movement → block) — MEASURED
Jonathan: the sail's context is initially "cloth + perpendicular + **movement**" — only ever used to block the
wind FOR movement; after the crisis the **movement** term upgrades to **block**, a more general term where
"block wind → movement" is one special case and "block water coming in" is another. So the same sail transfers
to a new goal (stay afloat) it was never built for. This sharpens §3's burning-context: the burn need not
merely **swap** a failing term — it can **upgrade** it to a more general **parent** that (a) subsumes the old
use and (b) enables **transfer**. That is abstraction (`SPHERE_GENERATOR` C.2's "closure-failure mints a
primitive," pointed *upward*), and it fills out what a context entry is: **place + orientation + history +
purpose ("for what")** — upgrading frees the term from a single purpose. Measured in `concept_upgrade.py`:

A tool is seen only in its **canonical** use (sail demonstrated blocking **air**). Media live in a feature
space whose **classes** (fluid `{air,water,steam}` / solid `{rock,sand}` / radiation `{light}`) are discovered
**unsupervised**. Ground truth: a tool solves a goal iff the operations match **and** the goal's medium is in
the **same class** as the demonstrated one (block generalizes *within* a medium class, not across). Over 35
novel (tool, goal) pairs (never the canonical one):

| representation | transfer recall | false-positive | accuracy |
|---|---|---|---|
| **SPECIFIC** (tied to the exact demonstrated medium) | **0.00** | 0.00 | 0.91 |
| **UPGRADE** (generalize the medium to its learned class) | **1.00** | **0.00** | **1.00** |

- **Headline:** sail on the NEW goal *stay-afloat* (block water) — truth **yes**; SPECIFIC says **no** (can't
  reuse the tool), UPGRADE says **yes** (transfers zero-shot). **Guard:** sail on *shelter* (block rock) —
  truth **no**; UPGRADE also says **no**. It generalizes the medium (air → fluid) but **keeps the class
  boundary**, so it never claims the sail can block a rockfall.
- SPECIFIC catches **0 / 3** true transfers — tying a tool to the exact context it was seen in makes it
  single-use. UPGRADE catches **3 / 3** with **zero** false positives: the movement→block upgrade is what lets
  one sail serve wind-block *and* water-block — the concept-level version of Test 12's rule-bending and Test
  11's sail+patch. `concept_upgrade.png`.

## 6. The context plane holds the MAP — coordinates need anchors AND orientation (MEASURED)
Jonathan: the matter (normal) plane can't see the orthogonal (context) plane, but the context plane **can**
see parts of the matter one — "parts sticking out." So the context layer reads a **map** with **coordinates**;
the matter plane is "a vast ocean with no references," so it can hold none. "We would need something to do
orientation though." This is localization from **bearings to anchors**, with orientation as the missing gauge.
Grounding: `FOLDING_VOID_LINE_DRAW` — the wall "emits a **bearing** to a field extension," and anchor points
"become visible on the **lift**" into the orthogonal axis (invisible in the matter projection, `INNER_SHELL`);
a pinned void line is a named anchor. Orientation = the frame: `FOLDING_TRAMPOLINE` §5 / `FOLDING_OBSERVER_FRAME`
— a single ring-stack "has a blind axis"; the three-ring (quaternion i/j/k) cage fixes any direction.
Measured in `orientation_map.py` (localize a position from bearings, 300 trials, 10×10 world):

| condition | mean localization error |
|---|---|
| **A — featureless ocean** (matter plane, no anchors) | **3.17** (unobservable ≈ prior) |
| **B — 2 anchors, NO orientation** | **2.23** (only an ARC — a 1-parameter ambiguity) |
| **C — 2 anchors + orientation (compass)** | **0.21** (located) |
| **D — 3 anchors, no compass (resection)** | **0.47** (located) |

- **The ocean has no coordinates.** With no anchors the position is unobservable — the best estimate is the
  prior (world center), error 3.17. "A vast ocean with no references," exactly.
- **Anchors without orientation give an arc, not a point.** Two relative bearings fix only the *subtended
  angle* (heading cancels), so the position lies on a locus — you know you're *somewhere on a curve* (error
  2.23). **This is "we need something to do orientation."**
- **Orientation collapses the arc to a point.** A compass (absolute bearings) pins it (0.21); and with **no**
  compass, a **third anchor sticking out** supplies the orientation by resection (0.47). So **coordinates need
  references AND a frame**, and the frame can come from a compass *or* from an extra anchor. `orientation_map.png`.

This says what the context plane *is*: the plane that can see the anchors (the parts sticking out, the pinned
void-lines, the high-variance gaps of Test 7) and, given a frame, read coordinates off them — a map the
featureless matter plane cannot hold.

## 7. Honest ledger
**MEASURED**
- **Burning context = Test-5 growth on the context plane** (§3): drifting environment, matter machinery fixed;
  fixed-context locks at mean error 0.184 (coin-flip after each drift), burn-context regrows the coordinate
  after every drift — 6 burns, mean error 0.037 (5× lower). `superfuel_context.py`.
- **Concept upgrade = zero-shot transfer** (§5): a tool seen only in its canonical use — SPECIFIC (exact
  medium) transfers 0/3 true novel-goal pairs; UPGRADE (generalize medium → learned class) transfers 3/3 with
  0 false positives (sail → block water, but still refuses block rock). `concept_upgrade.py`.
- **Coordinates need anchors AND orientation** (§6): localize from bearings — featureless ocean 3.17
  (unobservable), 2 anchors no-orientation 2.23 (an arc), 2 anchors + compass 0.21, 3 anchors resection 0.47.
  `orientation_map.py`.

**GROUNDED (in theory, not measured here)**
- Three budgets = ψ/φ/vesica = void/matter/context (`SHOVELCAT_THEORY.md`; `Shovelcat_29` §3.6 ε void).
- Superfuel = Fire from Fuel+Heat, "cools into new Ground," compression-when-full (`Shovelcat_29` §9, §4.6);
  empty-tank collapse vs full-tank Fire are opposite events.
- Consciousness = collapse at a variable threshold; pressure forces collapse (`SHOVELCAT_THEORY.md`); collapse
  is the costly step (`FOLDING_HANDSHAKE` §4).

**HONEST BOUNDS**
- §3, §5, §6 are toys that isolate the *mechanism* (failure-driven context replacement; class-based
  generalization; bearings-to-anchors localization + gauge-fixing). All are known-good moves (online feature
  replacement; categorization/abstraction; three-point resection), framed in the theory's terms. Not full
  agent systems. In particular §5's upgrade generalizes to the *cleanly-separated* discovered class; a fuller
  version would learn the right generalization *level* (not too broad/narrow) from data and gate the upgrade
  on crisis, rather than assuming the class is given by a clean cluster.
- §2, §4 are design readings mapping Jonathan's picture onto existing theory (Fire economy; collapse
  threshold). Consistent and grounded, not independently measured.
- The identification "superfuel = Fire = burning context = collapse energy" is a *unification claim* — each
  piece grounded, the single identity across all of them the conjecture.

## 8. One-line
The three old budgets — void (ψ), matter (φ), context (the vesica) — overflow into a **superfuel** only when
full and compressed (Fire from Fuel+Heat, `Shovelcat_29` §9), and what that superfuel *burns* is **context**:
the same failure-driven muscle growth as `FOLDING_MOVEMENT` Test 5, run on the orthogonal context plane —
measured as a drifting-regime agent that burns its stale context coordinate and grows a new one after every
drift (0.037 vs 0.184, matter machinery untouched); the context term **upgrades by generalizing** (movement →
block), measured as **zero-shot transfer** — a sail seen only blocking air transfers to blocking water (3/3
novel goals, 0 false positives) while still refusing to block rock; the context plane is the one that can
**see the anchors** and read **coordinates** off them, but only with **orientation** — measured: a featureless
ocean is unobservable (3.17), two anchors without a frame give only an arc (2.23), and a compass or a third
anchor pins the point (0.21 / 0.47); and a **decision / consciousness** is the collapse of the three budgets'
accumulated weight across a variable threshold — the photon's wave-or-particle choice scaled up — with the
superfuel as the energy spent to collapse when normal physics can't.
