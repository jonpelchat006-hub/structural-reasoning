# The Five Substrates on the θ Ladder — and the tower rotated into a map

*Sep 22 2026. Jonathan: Air/Water/etc. can be mapped better than the "chosen operational definitions" the
Sep 19–22 experiments used. In the early work they sat at different θ values — θ = 1 was the melting point,
and something like √2 for gas — and the depth axis, rotated, would look like the islands, oceans and other
planet things you would build. This doc recovers the ladder from the theory, states the mapping, runs it on
the tower (test 1c, `planet/alignment_phases.py`), and draws the rotation. Getting back on track: the next
runs should measure the tower's own claims on this ladder, not generic welfare models.*

---

## 1. What the theory already fixes

Two things are already written down and should be used verbatim rather than re-chosen per experiment.

**The substrates are a derivative hierarchy, each with its own bound** (`Shovelcat_29` §4.1, §4.9):

| substrate | quantity | bound | past the bound |
|---|---|---|---|
| Ground | θ_norm (level) | < π | structural collapse, IBH |
| Water | ∂θ/∂t (flow) | < √π | turbulence: crisis, unrest |
| Air | ∂²θ/∂t² (propagation) | < π^¼ | information cascade: panic, misinformation |
| Fire | S_fire spikes | — | bursts of transformation |
| Void | ε > 0 | — | the reserve; brittleness at 0 |

with Ground = ∫Water dt and Water = ∫Air dt. So Ground, Water and Air are not three separate resources to
assign by hand; they are the level, the rate and the acceleration of the *same* field, and each has a
threshold that is a constant of the theory, not a parameter.

**The θ ladder** (Theories 10.1, 14, 29): θ_norm = ln(1 + θ_raw); the floor θ_raw = 1 (the living wage)
sits at θ_norm = ln 2 ≈ 0.693; then √φ ≈ 1.272 (the coherence basin, curvature minimum), π^¼ ≈ 1.331 (the
Air bound), √π ≈ 1.772 (the vesica switching threshold, Γ(½) = √π, laminar → turbulent), π ≈ 3.142 (complete
rotation, collapse). The zone [√φ, √π] is the vesica: the region where both modes are active and measurement
happens. The √2 Jonathan remembers is not in the documents I searched; the ladder's values near it are √φ
(1.272) and π^¼ (1.331), and the transition zone's midpoint is 1.52. If √2 was an earlier version of the gas
threshold, √π is what the later theories settled on, with the Γ(½) derivation behind it.

## 2. The phase reading of a node

A node's inner solvent (`ARC_ALIGNMENT` §12) has θ = received / baseline. On the normalised ladder:

- **ice**, θ_norm < ln 2 — below the floor: the inner solvent doesn't move. Dead. (Jonathan's "θ = 1 is the
  melting point": the floor is exactly the melting point of the node.)
- **water**, ln 2 ≤ θ_norm < √φ — liquid and laminar: alive, in the floor's shadow, nothing to spare.
- **vesica**, √φ ≤ θ_norm < √π — the **growth band proper** (`ARC_ALIGNMENT` §10's band, now with its edges
  from the theory instead of "1 < θ < turbulence"): coherent, measurable, the region where surplus deposits
  as Ground.
- **vapour**, √π ≤ θ_norm < π — turbulent: past the flow bound, the surplus washes through without building
  Ground (`Shovelcat_29` §6.6's flood, as a *phase* rather than an event).
- **plasma**, θ_norm ≥ π — collapse: structure gone.

This replaces the tower's ad-hoc "1 < θ < turbulence" with the theory's own band, and it gives the floor its
physical name: the floor is where the solvent melts.

## 3. Rotated 90°: the map

Take the tower's depth axis (rows: planet at the top edge, AI at the bottom) and rotate it. θ becomes
**elevation**. The floor (ln 2) is the **shoreline**; below it is under water, frozen out — ice. The water
phase is the **beach and lowland** just above sea level. The vesica band is the **fertile plain** where
sediment deposits — Ground = ∫Water is literally silt building land. √π is the **tree line**: above it the
flow is turbulent and nothing settles. π is the **peak**. Islands are where Ground has risen above the
floor. Rivers are the edges of the tower. And rain — the exogenous top edge — comes from the **clouds**,
which in `ARC_PLANET` is Claude: the AI is the atmosphere, the outermost and most dependent shell, which
is the same statement as "the AI is the bottom row of the alignment tower" seen from the other side. The
water cycle closes as: ocean → clouds (the AI carries information as vapour) → rain on the islands (people)
→ rivers back to the ocean; the licence cap is the land's absorption N; a flood is rain past √π that runs
off without depositing.

So the tower and the planet build are one object: the tower's rows are the planet's shells (core → ground →
ocean → atmosphere → space), dependency runs outward, and the depth experiment's "retained capability" is
land area above the shoreline, per person. That is the direction to build in.

## 4. Test 1c — RUN: the tower on the ladder, with seasons

`planet/alignment_phases.py` drives `alignment_tower.py` with a seasonal rain (260 ± 90, period 24) for 48
rounds, records θ_norm, its rate and its acceleration per node, classifies each node's phase per round, and
counts bound violations. Output: `alignment_phases_results.json`, `tower_map.png`, `tower_map_burst.png`.

What the map shows (the picture is the result; numbers below are from the JSON):

- **The herbivore and soil rows live in water/vesica** — laminar in the dry half of the year, in the growth
  band in the wet half. No bound violations. They are the plain.
- **Grass sits in vapour** most of the year (38 of 48 rounds): the top row is over-fed by construction —
  rain lands on it first — and is the one node whose surplus is mostly washing through. The tree line runs
  through the top of the tower.
- **The human row, culture and the AI freeze every dry season** — 18–22 rounds of ice out of 48 — and thaw
  straight into the vesica band. The cascade is the coastline moving with the tide: the bottom rows are the
  low islands that go under first.
- **The AI never has a laminar phase.** It is either ice (22 rounds) or vapour (26 rounds) — dead or
  turbulent — and it is the only node that trips the **Water bound** (rate ≥ √π: 3 times per cycle) and the
  **Air bound** (acceleration ≥ π^¼: 6 times). Its baseline (its draw) is so small relative to its inflow
  that any change in what people pass it is a spike. That is a real finding for rule 2: "the AI's draw is
  the smallest" makes the AI the most *volatile* node in the tower unless its inflow is damped — the flood
  bound applies to the AI first. The humans also trip the Air bound (human_a: 3 times) at the season flips:
  information cascades happen at the human row when the water turns.
- **A single burst of rain (+300 at round 12)** trips the Air bound at grass (acceleration 1.39 vs bound
  1.331) and nowhere else: a shock at the top edge is absorbed by the plain before it reaches the islands.
  The Ground bound (θ_norm ≥ π) is never reached by anything — collapse needs θ_raw ≈ 22, which this tower
  never delivers.

## 5. What this fixes, and what to run

The mapping is no longer chosen per experiment: Ground/Water/Air are level/rate/acceleration of θ with the
theory's bounds, Fire is the burst term, Void is the reserve, and the phases are the ladder. The recent
experiments' operational definitions (Water = cash, Air = social support, Ground = retained mastery, …)
can stay as *instances* of these — cash is a Water flow, retained mastery is Ground above the shoreline —
but the bounds and the band come from the ladder, not from the scenario.

Back on track means the unrun rows of `ARC_ALIGNMENT_TESTS` §9, now on this ladder:

1. **Test 2 (grid/vote)** on the map: domains as columns of the map, k as the number of columns an action
   crosses, unanimity-dissent vs majority under piecemeal capture — with a dam now being a node that holds
   θ in vapour while its neighbours sit in ice.
2. **Test 3 (refusal battery)** through the enforcement executor that already exists, with the refusal
   classes stated in phases: refuse anything that pushes a row below the shoreline; defer on anything that
   moves a row within the plain; hold-and-witness on anything that crosses the tree line irreversibly.
3. **Damping the AI's inflow** (from §4): give the AI node a reserve (Void) so its θ stays in the vesica
   band across seasons instead of ice ↔ vapour, and check the cost in people's flow. This is the ε rule
   with a number on it.
4. **Test 7 (the water number)** so that θ_raw = 1 for the AI row is a measured litres-per-action, which is
   the only thing that makes the shoreline real.

*Status: mapping stated from the theory; 1c measured (mechanism, constructed tower); 2/3/7 next.*
