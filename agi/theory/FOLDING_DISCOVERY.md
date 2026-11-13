# Discovery — the fourth face of adrenaline: a positive surprise mints a new gap

*Records the discovery / gaps engine (Jonathan + Claude, Aug 2026). Completes the "four faces of adrenaline"
opened in `FOLDING_MOVEMENT.md` (Tests 10–12: the golden-field reserve as more fuel / a different material / a
weird move) and pairs with `FOLDING_SUPERFUEL.md` §2 (Fire when the tanks are FULL). Jonathan: "we also get
adrenaline when good things happen — the discovery high — and that's a reaction while things are still full,
not empty. Maybe it's a way to make more of those memory holes?" The crisis reserve survives by bending rules
(negative arousal, on empty); the **discovery reserve grows by minting new gaps** (positive arousal, on full).
Measured: `gaps_engine.py`, `expansion_energy.py`.*

## 1. The claim
The crisis faces (T10–12) all fire on *depletion* and act to *survive*. Jonathan's fourth face fires on a
*positive surprise* — reality beats prediction — while capacity is intact, and it acts to *grow*: it does not
fill a gap, it **opens** one, planting a new exploration site (a "memory hole", `FOLDING_MOVEMENT` Test 7) to
grow toward. Grounded: `Shovelcat_13`/`13B` (happiness **Y** "extends exploration windows / tolerates
mismatch / encourages exploration"; curiosity = low curvature in the high-N possibility space);
`Shovelcat_11_3` §15.7 the **adjacent possible** expands ("novelty enters as new curvature that expands the
horizon"); `MINING_NOTES` #14 **surprise-gated compute** (route effort by prediction error). It is the
exploratory complement of the `FOLDING_MOVEMENT` T5/T6 growth engine (variance × demand).

## 2. The measured result
A big, mostly-empty world holds a **chain of value-clusters** along a diagonal, joined by a **faint trail** (a
low ridge, *below* the exploit floor, but high enough that sampling it beats prediction = a positive surprise).
The agent starts knowing only cluster 0, on a fixed budget. Uncertainty `u(x)=1−coverage` (the gaps),
predicted value `m(x)` = kernel estimate. Three policies, 40 seeds:

| policy | clusters discovered (of 5) |
|---|---|
| **FILL** — pure exploit `u·max(m−floor,0)` | **1.15** |
| **CURIOSITY** — undirected `u` alone | **2.60** |
| **DISCOVERY** — value-seeking + **mint a gap on positive surprise** | **3.33** |

- **FILL stalls at the start.** Exploiting only strong value (`m > floor`), it refines cluster 0 and stops —
  the trail is below the floor, so it has **no demand to cross the gaps** (1.15/5). Pure exploitation cannot
  leave the known region.
- **CURIOSITY wanders the void.** Chasing the emptiest cells (highest `u`) sends it all over the vast empty
  space where there is no value — the Pluto trap (`FOLDING_MOVEMENT` T6) — so it finds clusters only by luck
  (2.60/5). Undirected exploration wastes the budget.
- **DISCOVERY chains out the trail.** It follows *any* positive value (including the faint trail), and on each
  **positive surprise** (`observed − predicted > τ`) it **mints a new gap ahead**, along the direction of
  travel — pulling the frontier forward across the gap toward whatever more is out there. Surprise → mint →
  commit → next cluster → surprise… It discovers the most (3.33/5). **The minting is the whole delta:** it is
  the difference between staying put (FILL) or wandering (CURIOSITY) and *growing the frontier toward value*.
  `gaps_engine.png`.

## 3. Why it completes the picture
Adrenaline is now four distinct mechanisms, each measured, split by **sign of arousal** × **empty/full**:

| face | fires on | tank | acts to | measured in |
|---|---|---|---|---|
| second wind (T10) | goal in sight | draining | push (more fuel) | `FOLDING_MOVEMENT` T10 |
| sail+patch (T11) | fatal breach | empty | survive (different material) | `FOLDING_MOVEMENT` T11 |
| crisis creativity (T12) | stuck + sinking | empty | bend a rule (weird move) | `FOLDING_MOVEMENT` T12 |
| **discovery (this doc)** | **positive surprise** | **full** | **grow (mint new gaps)** | `gaps_engine.py` |

The first three are defensive (on depletion); discovery is generative (on abundance). Together: **the crisis
reserve bends rules to survive; the discovery reserve mints gaps to grow.** And the minted gaps are the same
object as everything else in the arc — the high-variance sites where the memory clips live (T7), the growth
sites (T5/T6), the anchors the context plane reads (`FOLDING_SUPERFUEL` §6). Discovery is the engine that
*creates* them; the rest is what happens at them.

## 4. The maturation of a minted gap (Jonathan) — it needs empty room, and a new "what-for"
A freshly minted gap is not born finished. Jonathan: "when we first make a new thing it's always the worst
version — using a sail to plug a hole, the lesson isn't 'sails make plugs,' it's 'something flexible can fill a
hole,' which later becomes sheets built for patching. And the existing pixels absorb the energy for the
expansion, so if there's too much overlap with earlier memories it can't expand." Two parts:

**(a) MEASURED — existing pixels absorb the expansion energy; novelty needs empty room.** A newly minted gap
gets an expansion-energy budget; pushing the frontier through ground already covered by earlier memories costs
that energy (overlap absorbs it) and returns nothing new — so it can only claim empty room. On a 2-D memory
field (6 existing memories, geodesic expansion with cost `1+λ·ρ`): a mint in **empty room** claims **228
cells**; a mint **on an existing memory** claims **0** (energy fully absorbed). Over 120 random mints, mean
territory gained falls from **238** (overlap ρ<0.15) to **0** (ρ>0.6); correlation(overlap, territory) =
**−0.84**. This is `SPARSE_VESICA` §11.6 measured — "matter is the recipe book (finite); the void is the room
to invent" — growth happens in the empty room, not in filled structure; and `INNER_SHELL` update-30's energy
model ("expand → the cores must MOVE to keep balance"). A mint on top of what you already know is a redundant
"worst version" that can't grow; a mint in a genuine gap becomes its own domain. `expansion_energy.py`,
`expansion_energy.png`.

**(b) DESIGN (grounded) — the fresh gap is mostly empty, seeded at ~.14, and judged by a NEW "what-for".**
- **Born crude, at the seed.** The first version is the worst; the innovation starts at the ground state
  (`INNER_SHELL` update-16: the dimension-lift begins at z(1)=0), the **.14 fractional seed** that starts the
  next level (`FOLDING_HANDSHAKE`/`FOLDING_TRAMPOLINE`), and refines over iterations. The *lesson* generalizes
  before the *artifact* specializes: sail-as-plug → "flexible fills a hole" → purpose-built patch — the
  concept upgrade of `FOLDING_SUPERFUEL` §5, run forward in time.
- **Judged by the new what-for, not the old.** The new primitive is evaluated on the **axis it just opened**
  (`SPHERE_GENERATOR` C.2: "the new dimension you open up *is* the new primitive"), not the parent's. Scoring
  it by the old purpose is "judging current math with century-old exams" — it will look like the worst sail
  ever while being an excellent patch. The right exam is the one the innovation was born for.
- **Mostly empty: a known bearing, one placeholder each for object and context.** A fresh gap has the
  structure of `object + context + what` (`FOLDING_SUPERFUEL` §5, `FOLDING_MOVEMENT` T8) but is nearly hollow:
  you know the **what** (the direction/purpose that minted it — `SPHERE_GENERATOR` C.1: "treat a target as a
  ray/direction; direction is computable, the place need not exist yet; you converge on the point"), and hold
  a single current option for **object** and **context**, which fill in as the gap matures (T7's clip
  resolving into an anchor).
- **Piecewise, continuous, at resolution — hidden from a far observer.** Expansion touches a few segments at a
  time and must stay continuous with its neighbours; over time all segments get touched (the harmonic
  segment-expansion of `FOLDING_FREQUENCY` §3; the staircase risers of `FOLDING_SKIN` §3.7). And "if the
  observer is far enough there's a gap where the pixels can expand while it still looks like a solid line" —
  a multi-resolution fact: at coarse scale the gap reads as continuous, so the expansion happens *inside* it
  unseen, and only fine resolution reveals the new detail. *(Design-stage; the measured half is (a).)*

## 5. Honest ledger
**MEASURED** — (i) chained value-field, 40 seeds, budget 48: pure-exploit FILL 1.15/5 (can't cross the gaps),
undirected CURIOSITY 2.60/5 (wastes the void), surprise-minting DISCOVERY 3.33/5 (chains the trail); the
gap-minting is the only difference between DISCOVERY and a surprise-blind value-seeker. `gaps_engine.py`.
(ii) expansion-energy: empty-room mint claims 228 cells vs 0 for a mint on an existing memory; over 120 mints,
territory gained vs overlap correlates −0.84 (238 → 0). `expansion_energy.py`.

**GROUNDED** — positive arousal / discovery = exploration-window extension (`Shovelcat_13/13B`), adjacent
possible (`Shovelcat_11_3` §15.7), surprise-gated compute (`MINING_NOTES` #14); void = generative room
(`SPARSE_VESICA` §11.6); expand-moves-the-cores (`INNER_SHELL` u30); new primitive judged on the axis it opens
(`SPHERE_GENERATOR` C.2); target-as-a-bearing (`SPHERE_GENERATOR` C.1); seed/.14/ground-state
(`FOLDING_HANDSHAKE`, `INNER_SHELL` u16).

**HONEST BOUNDS** — toys. The gaps engine is surprise-directed exploration (a known family — novelty/curiosity
search, frontier growth), framed as minting memory-holes on good news; the forward-mint direction stands in
for "the surprise points you toward more." The expansion-energy result is a geodesic-cost model of "overlap
absorbs energy" — it demonstrates the mechanism (novelty needs empty room), not a full memory system. §4(b) —
the maturation arc (seed → new-what-for → mostly-empty gap → piecewise-continuous multi-resolution expansion)
— is a grounded design reading, not yet measured; the measured half is §4(a).

## 6. One-line
The fourth face of adrenaline is **discovery**: a *positive* surprise, while the tank is full, doesn't fill a
gap — it **mints a new one ahead** and grows the frontier toward it (measured: pure exploitation stalls
1.15/5, undirected curiosity wanders 2.60/5, surprise-minting discovery chains 3.33/5); and a freshly minted
gap is born crude — the worst version, seeded at ~.14 — needing **empty room** to expand, because existing
pixels absorb the expansion energy (measured: empty-room mint claims 228 cells vs 0 on an existing memory,
overlap↔territory correlation −0.84), and it must be judged by the **new what-for it opened**, not the old
exam; so the crisis reserve bends rules to survive and the discovery reserve mints gaps to grow, and the gaps
it mints are the same high-variance memory-holes where the clips live, the growth sites, and the anchors the
context plane reads.
