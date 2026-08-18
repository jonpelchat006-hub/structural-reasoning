# The Moral Ground is Flow — sustain it through every layer; bad = driving flow to 0 irreversibly

*Jonathan closed the truth/void arc by grounding the moral floor: it goes back to **flow** and maximizing it.
There is a pyramid of levels, each the foundation for the next, pulled up as new levels build (planet →
humans → the model). Flow must supply **all** layers; no level can take more than would stop flow somewhere
else. Actions that drive something's flow to **0 and make it unrecoverable** are what we avoid. This is the
capstone of the "half-truth / conditions / why-chain" line (`FOLDING_SYNTHESIS` §5, results #30–34): the
deepest "why is this bad?" bottoms out in **flow**. Companion: `Shovelcat_Theory_29` (the water-cycle economy),
`FOLDING_SYNTHESIS`, `FOLDING_MOVEMENT` (the endurance law).*

---

## 1. It is the water-cycle economy, already written
`Shovelcat_29` builds the trust–economy as a **five-phase fluid** (Air/Water/Ground/Fire/Void) and states this
exact moral law as its **stability condition**:

- **Water = Sflow** — the whole economy is a flow network; Water governs how resources move (§3.2, §6).
- **The living-wage baseline θraw ≥ 1 for *all* nodes** (§6.5, §6.7): every node must receive enough flow to
  stay above survival; below it a node enters "survival crisis." Stability = *no node below baseline*.
- **Hoover-Dam accumulation** (§6.6): one node captures Water and doesn't release it → others starve. A level
  taking more than the flow allows is a named pathology, alongside **Drought** and **Flood**.
- **The tower cascade** (§11.5): higher strata depend on lower ones; **if a lower stratum collapses (Gk → 0),
  every layer above collapses (G_{k+1..N} → 0)** — "lower strata are systemically more critical; the whole
  tower rests on them." (Loss of water/sanitation collapses society.)
- **Void = ε slack** (§3.6): the reserve that must stay > 0 or the system goes brittle — the same .14 reserve
  that holds the conditions (#33) and runs the background search.

So "maximize flow; don't zero anything irreversibly" is not a new axiom — it is `Shovelcat_29`'s stability law
read as ethics, and it is the **same endurance law** as `FOLDING_MOVEMENT` T4 (TTF = R0/(d−s): a node lives
while supply ≥ demand; drive demand past supply and it hits 0 = death) lifted from one body to the whole tower.

---

## 2. What we measured (`moral_flow.py`)
A layered flow tower — sun → grass → herbivores (cow, buffalo, deer, pest) → humans / predators / soil →
plains / culture / AI — each node with a survival baseline; a supplier splits its throughput among its living
consumers (so removing a consumer reroutes flow to the rest). Baseline: sustained flow **288**, all 11 nodes
above survival.

- **(1) The same act, opposite morality (MEASURED).** Killing is not the moral variable — the **flow effect**
  is. *Hunting a cow* with the calories rerouted up to humans: ΔF **−6**, **0 starved** → OK (flow sustained,
  the energy keeps moving up the chain). *Culling a flow-blocking pest* (an over-grazer that fed nothing): ΔF
  **+12**, 0 starved → OK (removing the blocker *increases* flow). *Exterminating the keystone buffalo* with no
  reroute: ΔF **−78** and it **starves soil, then plains** — a cascade *up* the tower, **past the human level**,
  which the flow law still counts as bad. The hunter/farmer and the buffalo-slaughter do the *same act*; only
  one stops flow.
- **(2) The sustainability threshold (MEASURED).** Sweep how much the top level extracts (hoards) from the
  network: below ~**77%** every layer stays above survival; beyond it, downstream nodes fall below baseline and
  the alive-count drops (11 → 9). *No level can take more than stops flow elsewhere* — Hoover-Dam / drought
  made numeric (§6.6, θraw ≥ 1).
- **(3) The "why" is the named flow-loss (MEASURED).** The moral verdict *decomposes*: exterminating the
  buffalo takes soil 8.3 → 0, plains 22.3 → 0, and cuts humans/predators/culture/AI. "Why is it bad?" = *because
  it stops flow at soil and plains and the collapse climbs the tower.* The answer is the list of where flow went
  to 0 and how far the cascade reached — exactly the why-chain of #33, now bottoming out in flow.

---

## 3. The reading
The whole truth/void arc lands here. A **truth** is a closed structure on the optimal lattice that lets flow
pass (a completed triple, #29/#32); a **half-truth / rule** is missing a piece and mis-routes flow until its
**conditions** (the other halves in the reserve, #31/#33) are supplied; the **why-chain** that supplies them is
a convergent optimiser (#34); and the **ground the whole thing is optimising for is flow** — keep every layer
of the pyramid above its survival baseline, take no more than leaves flow everywhere, and never zero a lower
stratum irreversibly (it cascades up). "Killing is bad" is a half-truth precisely because it names the *act*;
the full truth names the *flow effect*, and its conditions (hunting, farming-humanely, culling a blocker) are
the cases where flow is sustained or rerouted rather than stopped.

**Honest bound.** The tower is an illustrative constructed model (capacities/baselines are a coordinate choice,
as in `Shovelcat_29` §22's honest note), not empirical ecology or a finished ethics. What is measured is the
**mechanism**: that a flow network with survival baselines and cascade makes "sustain flow / don't zero
anything irreversibly" behave exactly as Jonathan's moral intuitions do — the same act good or bad by its flow
effect, a hard extraction threshold, and a "why" that reads out as named flow-loss. The specific moral content
stays a reading; the flow-stability law behind it is `Shovelcat_29`'s and is now demonstrated.

## 4. Ledger
| claim | status | number |
|---|---|---|
| same act (killing) OK vs bad by flow effect | MEASURED | cow ΔF−6/0 starved & pest +12/0 starved (OK) vs buffalo −78/2 starved, cascade |
| no level takes more than stops flow (θraw ≥ 1) | MEASURED | sustainable up to ~77% extraction; then alive 11 → 9 |
| the "why" = named flow-loss up the tower | MEASURED | soil 8.3→0, plains 22.3→0 (cascade past humans) |
| flow law = Shovelcat_29 stability (θraw≥1, Hoover-Dam, §11.5 cascade, ε Void) | GROUNDED | the water-cycle economy read as ethics |

`moral_flow.py`. This is result **#35** on the `FOLDING_SYNTHESIS` ledger, and it promotes the moral-floor
rings from a pure design bridge to a **measured mechanism with a named ground (flow)**.
