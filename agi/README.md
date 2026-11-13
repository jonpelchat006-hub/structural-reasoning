# The cognitive-architecture thread — "the baby brain"

*An attempt to grow a general-reasoning agent **from the bottom up**: a fixed inner shell that carries no
knowledge but carries whatever lets it grow, a learning middle shell that acquires skills from what it is
shown, and a domain-shaped outer shell that takes the form of whatever it is pointed at. The frame
throughout is Jonathan's: **we are growing an empty baby brain.***

The stance matches the rest of this repository: **name the claim, build a runnable experiment, and believe
the number — even when the number bounds the idea.** Every result below is a self-contained Python script
that prints its measurement and saves its figure. The split between what is **measured** (a runnable number)
and what is **grounded design** (consistent with the framework, not yet its own result) is kept explicit in
the master ledger, [`theory/FOLDING_SYNTHESIS.md`](theory/FOLDING_SYNTHESIS.md).

## What is here
- **`code/`** — 55 self-contained experiments (`numpy`/`scipy`/`matplotlib`/`networkx`), one per result.
- **`figures/`** — the figure each experiment saves.
- **`theory/`** — the master ledger (`FOLDING_SYNTHESIS.md`) plus dedicated write-ups
  (re-basing, trust/stitch, the outer-shell workspace, the moral-flow ground, encryption, what-it's-for)
  and the session notes around them (movement, superfuel, frequency, discovery, the handshake, the
  trampoline, the combine membrane, the galaxy bridge).
- **`baby_brain_map.html`** — an interactive one-page map of the whole architecture.

## The three integrations (the spine of the thread)
- **#37 — the first integration (memory):** the memory pieces run as **one agent** on a regime-switching
  stream; each ablation fails exactly where its piece was cut. `baby_agent.py`
- **#49/#50 — the second integration (discovery):** antenna → extrapolate → probe → trust(confirm/surprise)
  → fill/mint, reserve-gated; directed discovery beats random & exploit, surprises land on real structure.
  `discovery_loop.py`, `discovery_bulb.py`
- **#51 — the third integration (remember + discover):** one agent that both recalls solved regimes and
  discovers novel ones, growing on an open stream — **0.91 competence** vs each ablated half ~0.20.
  `agent_grow.py`
- **#55 — the perception rung:** the agent earns the regime signature from **real pixels** by steering the
  right lens-cone into focus (right lens 1.00, wrong near chance; select beats stack). `perception_lenses.py`

## The full measured ledger (55 results)
Each row: result · one-line claim · headline number · home doc. `MOVEMENT`/`SUPERFUEL`/`FREQUENCY`/
`DISCOVERY` refer to the companion docs (`FOLDING_MOVEMENT.md`, `FOLDING_SUPERFUEL.md`,
`FOLDING_FREQUENCY.md` and `FOLDING_DISCOVERY.md`, all in `theory/`);
`SYNTHESIS §n` is a section of the master ledger.

| # | result | number | doc |
|---|---|---|---|
| 1 | IK null-space reserve reaches + unjams | 87.3% vs 77.0%, 41 vs 197 jams | MOVEMENT T1 |
| 2 | bidirectional / seam = min-cut (not frontier-meet) | 0.90× / refuted | MOVEMENT T2 |
| 3 | sustain a pose off the floor on reserve | −0.28 vs −0.99 | MOVEMENT T3 |
| 4 | endurance law exact | TTF = R0/(d−s) to the tick | MOVEMENT T4 |
| 5 | growth into the empty tail = capability | frontier 0.75→0.98; fixed = 0 gain | MOVEMENT T5 |
| 6 | GP variance = don't-know; growth = variance × demand | gap var 15×; 0 wasted on Pluto | MOVEMENT T6 |
| 7 | memory clips live in gaps; resolve → anchor; worst-first | 21/21; 18% less error | MOVEMENT T7 |
| 8 | return path; real context seals the bottle | 0.214 → 0.013 (−94%) | MOVEMENT T8 |
| 9 | space-time bubble = delay window (Takens) | v-RMSE 1.45 → 0.016 (1→2 frames) | MOVEMENT T9 |
| 10 | second wind — goal-gated reserve | 134/200 vs 81; always-on mass → 0 | MOVEMENT T10 |
| 11 | sail + patch — survival via unfolded mass | 140/140 vs dead at 32 | MOVEMENT T11 |
| 12 | crisis creativity — Fire crosses the rule-border | 222/240 vs rigid 0/240 | MOVEMENT T12 |
| 13 | superfuel = burning context (orthogonal growth) | 0.037 vs 0.184; 5× lower | SUPERFUEL §3 |
| 14 | concept upgrade = zero-shot transfer | 3/3 transfers, 0 false-positive | SUPERFUEL §5 |
| 15 | coordinates need anchors AND orientation | 3.17 → 2.23 → 0.21 / 0.47 | SUPERFUEL §6 |
| 16 | frequency = spin-identity + harmonic expansion | 1.00 vs 0.18 under spin; 0.41→0.00 | FREQUENCY |
| 17 | discovery = mint gaps on positive surprise | 3.33/5 vs 1.15 / 2.60 | DISCOVERY §2 |
| 18 | existing pixels absorb expansion energy | 228 vs 0 cells; overlap↔gain −0.84 | DISCOVERY §4a |
| 19 | thinking = search per budget; spin needs a spectral method | vol 100% / orient 64% / spin 14% → FFT 100% | SYNTHESIS §6 |
| 20 | perspective swing — pivot the frame around an anchor | raw view 0.62 → swung view 1.00 | SYNTHESIS §5 |
| 21 | the memory loop end-to-end (mint→store→seal→anchor) | looped 0.056 vs baseline 0.214 | SYNTHESIS §4 |
| 22 | the observer defines the cycle → memory → its gaps | HR 4 memories/gap 0.33 vs VO₂ 11/gap 0.77 | SYNTHESIS §4 |
| 23 | cycles paint a new object; type = endpoint relation | light ridge @1.45 vs heavy @0.99; ω↓/Φ○/r↑ | SYNTHESIS §5 |
| 24 | ring of truths — verify through a gate; steer = attention | steered 1.20 @cost 6 vs check-all 0 @cost 60 | SYNTHESIS §5 |
| 25 | does the cycle close? rational loop vs irrational torus-fill | 3/2 returns @t=2; φ never; store-saturates vs ~1/√B | SYNTHESIS §5 |
| 26 | encryption across axes — full key set; public/locked/hidden; lock=irrationality | no-keys 1.813 → full 0.048 (floor=hidden); rational cracked @Q=3, golden never | ENCRYPTION |
| 27 | recall over an expanding pillar field — reproject / absorb / surface | frozen 1.36 vs reprojected 0.00; absorb corr +0.93; surfaced spread 2.8× | SYNTHESIS §4 |
| 28 | structural pillars · finite viewing band = capacity · similar memories blend | band 4 / reach-cap 14; drag 55% vs direct 25%, +4 context; instance 100%→19% | SYNTHESIS §4 |
| 29 | perspectives carve a cube → sphere (void point); ping-pong redundancy | protrusion 1.26→0.002; 3D vol 32.8→4.26; isotropy spread →0.0006; marginal cut→0 | SYNTHESIS §5 |
| 30 | skew → a bouncing ball (Hopf); off-void unanchored approx. void point | balanced→void pt (r=0); skewed→limit-cycle ball (√μ, start-spread 0.000); miss-void 0→0.6 | SYNTHESIS §5 |
| 31 | balls are half-truths (missing opposite); void is relational; balance=mass | residual 1→0.5→0 w/ opposite; definedness 0→0.95 w/ surround; mobility 1.0→0.04 | SYNTHESIS §5 |
| 32 | completing a half-truth = inverse triple (Erdős orchard); closed & self-similar | 1pt free→2pt forced; closure 100% vs 0%; self-similar only at φ/φ² | SYNTHESIS §5 |
| 33 | a rule is a half-truth; conditions = other halves in the reserve; why-chain crosses territories | "killing is bad" err 0.29→0.00 w/ conditions; halo 51/31/46%; acc 0.79→1.00 across axes | SYNTHESIS §5 |
| 34 | completing triples finds the optimum from any start; two-stroke (knot+tail); surround pins it | 10 starts → same optimum; 90% by iter 210, tail longer; anchors 451→141→38 | SYNTHESIS §5 |
| 35 | the moral ground is flow; bad = zeroing a stratum irreversibly (cascade) | same act OK vs bad by flow; sustainable ≤77% extract; buffalo cascade soil→plains→0 | MORAL_FLOW |
| 36 | breaks in continuity set where cycles begin/stop; perspective pinches off a segment | HR line → 5 animal segments; masks 83–94%; global mean 393 bpm lands in a gap | SYNTHESIS §4 |
| 37 | **the first integration** — the pieces run as ONE agent; each ablation fails where its piece was cut | integrated 322 / revisit 0.72 vs memoryless 99/0.22, no-segment 130/0.35, no-gate 34/0.00 (breakdown) | SYNTHESIS §10 |
| 38 | orthogonal lenses (each a cosθ·vᵈ derivative chain) decompose the workout; attention is finite | 1 lens 48% → 3 lenses 100%; cos²+sin²=1; breadth 4→1 with zoom | SYNTHESIS §4 |
| 39 | continuous-stream I/O — emit chunks on COMPLETION (the snake) not on a clock; route by domain | snake 100% whole / 0 cut / 22-22 usable vs clock 0% / 16 cut / 6-22; .geo text/audio(violin)/image | SYNTHESIS §4 |
| 40 | **rung 2** — a LEARNING agent on a switching-goal gridworld, benchmarked honestly (6 seeds) | revisit steps: SHOVELCAT 11.1±2.7 vs Q-regime 12.3±3.0 vs Q-pos 34.9±3.1 (modest but real) | SYNTHESIS §10 |
| 41 | memories UPGRADE on revisit; spore-chain direction sprays important memories to the top; reuse resurfaces | recognition 0.80→1.00 vs frozen flat ~0.8; importance↔depth corr −0.88; reuse depth 8→0.8 (~10× recall) | SYNTHESIS §4 |
| 42 | folding #41 into the agent — upgrade is only safe under trusted association; blind averaging contaminates → gate it | hard-probe recog +11pts (0.62→0.73); contamination crossover ~42%; full agent a wash (0.75/0.76/0.73) unless gated | SYNTHESIS §4 |
| 43 | the trust gate made functional (regression test) + stitch the gaps; the folded ball's trust = what it's made of; per-lens, branch-switchable | naive replace loses 7 caps vs gate 0; stitch covers 11 vs 7/8; 1-layer ball trust 0/.67/1/0 vs diverse 1/1/1/1; branch-switch 1.0→0.0 | TRUST_STITCH |
| 44 | recall = montage to a topic template (cut across movies); void reserve gates consolidation — fast collapses & blends, calm layers | canonical query 33% cross-cuts vs experience 0%; provenance recovery 0.92→0.39, separable 1.0→0.07 across collapse rate ~2.5 | SYNTHESIS §4 |
| 45 | what an unknown values = the invariant (common to/moves all), not a spurious confound; topic = the upgradable border, ball = substance | one-sample selector R² −0.53 OOD vs invariant 0.96; shared×stability separates confound; border upgrade 0/4→4/4 | SYNTHESIS §5 |
| 46 | neuroplasticity = reroute A→B around a lesion through similar-enough neighbours; fails only on endpoint isolation | direct corridor walled → reroute +2 detour; graceful vs % lesioned; connected until B's last neighbour cut | SYNTHESIS §4 |
| 47 | each pixel = the three-shell brain RE-BASED one notch (learned→core, domain→middle, fresh void→outer=reserve=intake port); unknown values = where the void fills | core innateness 1.0→0.09, reserve conserved ~0.17; intake only in void, port-gated; unknown target 1.00 open vs 0.58 closed | REBASING |
| 48 | the void antenna (a hair) — reach ∝ emptiness, antennae converge to localize unreached anchors, snap-ray-to-known extrapolates the unknown's values | reach↔emptiness corr 1.0, point-at-void cosθ +0.86; 100% voids recovered, anchors 2.5× decoy votes; ray-snap 13.6× better than blind | SYNTHESIS §4 |
| 49 | **the closed discovery loop** — antenna→extrapolate→probe→trust(confirm/surprise)→fill/mint, gated; runs as ONE system, ablations degrade | directed 0.33 vs random 0.38 vs exploit 0.75; surprises 58% on real anchors (~4× chance); reserve gated alive vs ungated breakdown −0.60 | SYNTHESIS §10 |
| 50 | the surprise is a BULB further out — densify the EMPTY lit region not the filled one (fixes #49's null); strength opens more pixels; fold back in | lit-empty +5.3% cov (0% overlap) vs in-place +0.0% (100%) = 53×; strength 1→8 lights 8→400 pixels; fold-in 27%→32% | SYNTHESIS §10 |
| 51 | **the third integration** — one agent REMEMBERS + DISCOVERS, growing on an open stream; each ablation fails where its half was cut | FULL competence 0.91 vs memory-only 0.19 / discovery-only 0.20 / no-gate 0.65 (breakdown); explores 21 vs 38 (amortized); store 0→34 | SYNTHESIS §10 |
| 52 | the outer shell = a workspace of frozen artifacts (dark matter); disk lifts storage not attention; far 'story' artifacts are spotlights; tools pluggable, work resumable | disk retained ∞ vs bio cap ~14, attention band 4 both; off-path bridge 0.95 vs unreachable; pluggable 100% vs fixed 31%; retained 100% vs discarded 0% | OUTER_WORKSPACE |
| 53 | the workspace is ORBITAL — artifacts orbit the planet; type sets period (revisit cadence through the telescope FOV) + view-effect; steer the orbit = attention | each ~20–25% in-view, 3 simul > band 2; image satellite clarity 0.87 vs dust 0.51 vs border 0.09; steer 1 vs wait 4 (=#24) | SYNTHESIS §4 |
| 54 | telescope lenses = observer perspectives at focal distances (borders out of the cone); stacking helps only if complementary AND accurate; sky taxonomy + distance-control | lens peaks at focal dist, border-zone dies; +complementary 0.31→0.55, +weak drags acc 0.91→0.83; drone self-places 14 vs asteroid 159 | SYNTHESIS §4 |
| 55 | **the perception rung** — earn the regime signature from REAL PIXELS by steering the right lens-cone; right lens separates, wrong near chance; select beats stack | right lens 1.00 vs off-diagonal ~chance; LEARNED=oracle 1.00 vs fixed 0.43/random 0.62; naive committee 0.72 (drag, #54) | SYNTHESIS §10 |

## Honest bounds
These are **toy-scale, self-generating experiments with exact ground truth** — clean demonstrations of the
architectural claims, not benchmark results on real tasks. Almost every mechanism is a *known-good* method
(null-space IK, active learning, Takens embedding, uncertainty sampling, invariant-risk feature selection,
graph rerouting, prototype recognition, …); **the contribution is the single geometry that selects and
connects them, and the discipline of measuring each one** so the map is honest about where the proven
ground ends and the design begins. The perception rung (#55) uses controlled synthetic pixels; the agents
(#37/#40/#51) run on synthetic streams. Real domains — natural images, a live game — are the next rungs.

## Reproducing
```bash
pip install numpy scipy matplotlib networkx
cd code && python discovery_loop.py   # or any other <result>.py — each prints its numbers and saves a .png
```
