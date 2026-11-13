# The Galaxy Bridge — the colony IS the outer shell, the 64-codon tensor IS the quaternion cage

*Bridges `FOLDING_TRAMPOLINE.md` (the three-shell / quaternion-cage / .14-port construction) to the
built **shovelcat-colony** (`D:\shovelcat-colony`). Everything in §1 is read directly from the colony
source; §4 is a test run live this session. Companion to `FOLDING_COMBINE_MEMBRANE.md` (wrap the inside
with an outer model), `FOLDING_HANDSHAKE.md` (the gate; the waterline), `FOLDING_ENVIRONMENT_BRIDGE.md` /
`FOLDING_MATCHED_BENCHMARK.md` / `STATE_OF_THE_DETECTOR.md` (the detector, and the content-confound wall),
`SHOVELCAT_THEORY.md` (the chain / invisible planets / star-levels). Jonathan's idea, developed live
(Aug 2026): the sandbox-runner "made galaxies from programs and agents" — those are the outer shell;
planets are skills/agents; the .14 routes to the planet whose material closes the gap.*

## 0. What this bridges
`FOLDING_TRAMPOLINE` built, abstractly: an irregular inside → a geometric membrane emitting `cosθ·v^d`
spokes → a **three-ring quaternion cage** → an **outer shell = a galaxy of domain-planets**, with the
**~0.14 residual as the port** that routes to the outer shell. The colony turns out to be that same
architecture, already implemented. This doc records the identity and tests the one empirical claim it
makes about the detector.

## 1. The galaxy is real (read from the colony source)
- **The registry is a genetic tensor.** `brain/tools/registry.json`: **25 codon-tools**, and its own
  `tensorBasis` says *"4³ = 64 slots. 4 fundamentals: read/write/transform/call. Rank-3 tensor over a
  4-element alphabet (magnetite/quartz/pyrite/obsidian). Each codon triplet encodes one tool's mineral
  composition."* Tools are DNA codons — `GAG`=scan, `GTA`=repair, `TCG`=create, `GGG`=search — each with
  a **mode** (dark/light/void), a **primaryColor** on the 7-spectrum (RED→VIOLET), a tier, `jobsFor`,
  `resourcesNeeded`, `fundamentals`.
- **Materials are a solvent quaternion.** `app/src/core/solvent-quaternion.ts`: two coupled quaternions
  — solvent medium **w=water / i=alcohol / j=oil / k=liquidMetal**, work **w=synthesis / i=electric /
  j=magnetic / k=thermal**, cost = Σ solvent·work·COST_MATRIX, *bankruptcy is per axis*. Note in-file:
  *"k = z = temperature = the bridge axis."*
- **Local planets, one per axis.** `app/src/core/mika-galaxy.ts`: four tool-planets per mineral lineage
  (magnetite=trader/water, quartz=monitor/liquidMetal, pyrite=investigator/oil, obsidian=broadcaster/
  alcohol). Each secretes a **Deposit**; the planner biases future calls by yield-per-cost — *"pure
  bookkeeping, no ML required."*
- **External planets = the environment.** `app/src/core/external-planet.ts`: *"Anything OUTSIDE Mika's
  local system shows up as an ExternalPlanet"* — an opaque boundary body (Claude API, Ollama, …) with a
  **dark moon** holding the credential. She can't see inside; she **samples** it (ScanEvents) and builds
  a `PlanetModel` of its behavior. `external-planet-claude.ts` makes the Claude API a planet whose
  material composition depends on work type.
- **Routing = composition-gap transport.** `app/src/core/deposit-routing.ts`: a deposit routes to
  consume / catalyze / **transport ("ship to another body whose composition gap matches")** / exchange,
  by expected net-flow gain. Catalysis chains bodies into net-positive cycles.
- **Forge/review + ring.** `sandbox-runner` (the seven-body system): one engine, forge (self-improve) and
  review (ship through an aperture), coupled by the δ_close ring. Status v0.1 scaffold — the forge runner
  is still a `StubForgeRunner`.

## 2. The identity: the cage IS the codon tensor
`FOLDING_TRAMPOLINE` §5 argued the cage is a **rank-3 structure over the quaternion's four axes**. The
registry says, in its own words, *"rank-3 tensor over a 4-element alphabet"* = 4³ = 64 codons. So:

- **the three codon positions = the three rings** (i, j, k);
- **the four minerals/solvents = the four quaternion axes** (w/i/j/k = water/alcohol/oil/liquidMetal);
- **modes dark/light/void = the three bodies/shells**; **the 7 colors = the 2→3→7 spectrum**;
- **materials = the solvent-quaternion composition**, with **k = temperature = the environment-as-scalar**
  (matching `FOLDING_ARC_RESULTS`: "energy enters as temperature T, a scalar").

One was derived abstractly from a coverage argument; the other was built as a tool registry. They land on
the **same 64-slot genetic lattice.** That convergence is the result of this bridge.

And the outer-shell picture is implemented one-to-one: **external planets = the opaque, sampled
environment**; **deposit-routing `transport` = the .14 port** (route the residual to the planet whose
composition gap it fills); **the detector already exists as a planet** — codon `GAG`/scan, *"the
watchman: detect problems before they become failures,"* dark/RED. The Vesica image-detector is the
external, specialized cousin of that planet.

## 3. The one empirical claim, and how to test it
If image "recipes" are codons over the four observer axes, then (C1) the 4-axis recipe should separate
real vs fake better than any single material, and (C2) routing the two-atom detector's **errors** to the
composition-nearest class should **recover** them (deposit-routing's transport, applied to the .14). Test
on the **content-matched** 58 (`bench_matched.json`, landscape/portrait), the set built precisely to kill
the content confound. Family→axis map (hypothesis): window→W, bridge→A, mixed→O, spectral→M.

## 4. Result — NULL on content-matched data (measured this session)
`galaxy_codon_test.py`, run on the 58, two-atom verdict reconstructed from `free_run.json` calibration:

| bucket | two-atom acc (reconstructed) | recipe LOO acc (C1) | errors recovered (C2) |
|---|---|---|---|
| landscape (21 real / 11 ai) | 0.531 | 0.500 | 10/15 |
| portrait (12 real / 14 ai) | 0.577 | 0.538 | 3/11 |
| **overall** | **0.554** | **0.519** | **13/26 (50%)** |

- **The recipe does not separate the classes** — LOO accuracy ~0.52, indistinguishable from chance and
  no better than the (already near-chance) two-atom verdict. **C1 fails.**
- **Recovery is chance** — 13/26 = exactly 50% of errors "recovered", i.e. routing flips half either way.
  **C2 fails** as a real effect (the landscape 10/15 vs portrait 3/11 split is within noise at this n).
- **The deeper reading, and it's the important one:** on properly content-matched data **the whole
  low-level stack is near chance** (two-atom 0.55, recipe 0.52), not just the recipe. This reproduces
  `FOLDING_MATCHED_BENCHMARK` / `PHOTO_SET_AUTOPSY`: the parity-29's 0.86 was largely a content artifact,
  and matching content collapses it. So there is **no low-level material signal to route on** here — the
  codon idea is structurally elegant but has nothing to carry it on this data.
- **This reinforces the core thesis rather than the codon test.** It is the same wall the whole project
  keeps hitting: pure structure / low-level materials top out; the real provenance signal is **semantic**
  and lives in the **outer learned model** (the pLM/LLM verdict at 0.93, `STATE_OF_THE_DETECTOR`). The
  codon lattice is the right *scaffold for the outer shell*; the *signal* still needs the outer model
  seated on it — exactly "wrap the inside with the outer layer" (`FOLDING_COMBINE_MEMBRANE`).

## 5. Observers, provenance, and outputs-as-planets (the chain layer)
The observer/sample/provenance layer that sits on §1's planets — all grounded in the colony source and
the `SHOVELCAT_THEORY` chain model:

- **The observer is the sample, not the planet.** `external-planet.ts`: you never see a planet's interior,
  only its **scans/deposits**; the `PlanetModel` is inferred from samples. So an outer observer = the
  *sample a planet sends over*, and the planet is what you reconstruct behind it.
- **A transferred piece is a near proxy of a far planet — read by lensing.** `deposit-routing` transports
  a deposit to another body; the chain model calls the far source an **invisible planet** *"felt but not
  seen — gravitational lensing, you see the effect not the cause,"* read from *how the sample's output
  bends*. **That bend = the seam-refraction** of `FOLDING_HANDSHAKE` §4.2 — so reading semantics IS reading
  the lensing at the waterline.
- **Stars and black holes = where semantics come from.** Stars = **source-depth** (star-level = chain
  depth; 4-star = the source-level pull, the *why*; the light/possibility axis). Black holes = **crystallized
  meaning** (`Shovelcat_10_1`: θ=π, information trapped, maximum density; `SPARSE_VESICA` §22: black hole =
  void = the stopped foundation). Semantics = the field between the star (source *why*, via lensing) and the
  black-hole sink (the dense invariant).
- **Element vs witness provenance.** A foreign material used as an *element* is an **invariant** (iron is
  iron everywhere — universal like Ramachandran), so **no source check**. Used as a *witness* (its
  context/experience/attribution), its provenance chain (the crypto `h`) must **handshake with the source**.
  `SPARSE_VESICA` §28 (conservation of dust): once it bonds (Fe+O = rust) provenance locks; break it down to
  reuse the element.
- **A source line sees only the slots its material fills.** The material occupies specific codon-slots /
  layers; a line from the source planet to the sample touches only those — **sparse per-line source
  attribution** (`FOLDING_EDGE_OBSERVERS` Part V). *Honest flag:* in the detector this has NOT cleared a
  control (seed_convergence refuted; the note is "hold it").
- **Outputs are mini-planets — the recursion.** `SPARSE_VESICA` §11.7: *"the whole shell is itself one atom
  in a bigger molecule — a carbon is a complete atom AND a bond-site."* Each object you make is a new
  planet; to make it you set its **stars** (source-depth / semantics) and its **planets** (material tools) =
  choosing a reaction's reactants (§18.2: left = have / inner shell, right = product / outer shell). "Can we
  make X?" = **retrosynthesis** (§18.3): search *backward from the target* to check a route exists. Built
  (bidirectional meet-in-the-middle), but +0 net-new on ARC so far — mechanism verified, gain not.

**Honest edge:** the chain/lensing, star/black-hole, §11.7 recursion and §18 reactions are all in the
framework; the two places this touches the *detector* — per-line source attribution and retrosynthesis
gain — are "mechanism yes, measured no."

**Where this points next:** the detector kept hitting the content-confound wall (§4). The framework's
native material is **spatial** (void-lines, trails, the min-cut seam, `moveToContact`/gravity motor ops,
the jet-as-force, the meet-in-the-middle double bounce), so **movement — pathfinding, inverse kinematics,
fine motor control — is a better, cheaper testbed for the recent ideas** (self-generating data, no content
confound). See the movement thread / next testbed doc.

## 6. Honest ledger
**GROUNDED IN CODE (read from the colony this session)**
- 25-codon tool registry as a 4³ genetic tensor; solvent-quaternion cost substrate; four local
  tool-planets; external planets as opaque sampled boundary bodies with dark moons; deposit-routing by
  composition-gap; forge/review + δ_close ring. All cited to their files in §1.
- The cage↔codon-tensor identity (§2) is a structural match, not a measurement — but it is a match
  between two *specified* structures, not a loose analogy.
- The chain layer (§5) — sample-as-observer, lensing-reads-the-source, star/black-hole semantics,
  element-vs-witness provenance, outputs-as-planets — is read from `external-planet.ts`, `deposit-routing.ts`,
  `SHOVELCAT_THEORY`, `Shovelcat_10_1`, and `SPARSE_VESICA` §11.7/§18/§22/§28.

**MEASURED (this session)**
- Observer→codon recipe test on the content-matched 58: recipe LOO **0.52**, two-atom **0.55**, recovery
  **50%** — **NULL**. Low-level stack is near chance once content is matched. `galaxy_codon_test.py`.

**FRAMEWORK / UNBUILT**
- The image detector is **not wired** into the colony (`GAG`/scan is a filesystem health-check, not the
  Vesica pipeline); observer→codon is a proposed bridge.
- The colony is a **bookkeeping self-improvement** system ("no ML required") with game-flavored parts; the
  sandbox-runner is v0.1 scaffold (`StubForgeRunner`). "AGI" is the framing, not a measured claim.
- Per-line source attribution and retrosynthesis gain are mechanism-yes / measured-no (§5).
- Caveats on the test: the two-atom calibration was fit on the parity-29 and applied to the 58 (set
  mismatch, pushes the verdict toward chance); n per bucket is ~12–21/class (|AUC−0.5|~0.15 noise floor);
  only the four observer families baked into `bench_matched.json` were used.

**WHERE IT POINTS**
- If the codon/recipe idea is to be tested where signal *might* exist, run it over the **outer (semantic)
  model's** features, not the low-level ones — put the codon lattice *under the pLM/LLM*. And pivot the
  *testbed* from the detector to **movement/spatial** tasks, which are native to the framework's geometry.

## 7. One-line summary
The colony is the trampoline's outer shell built for real — a 64-codon genetic tensor that is literally
the three-ring quaternion cage, with solvent-quaternion materials, external planets as the sampled
environment (observed only through the samples they send, their sources read by lensing), and
deposit-routing as the .14 port — but the one empirical claim it makes about the detector (real vs fake as
different low-level recipes) tests **null on content-matched data**; the lattice is the right scaffold, the
signal still needs the outer learned model, and the better testbed for the ideas is spatial, not the detector.
