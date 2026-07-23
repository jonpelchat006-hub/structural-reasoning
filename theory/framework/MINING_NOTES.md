# Mining notes — ideas to close the train→eval gap

Context: the solver reaches ~20% on the **training** set but does not transfer to
**eval**. Diagnosis and a ranked list of mechanisms found across the old projects
(`Vesica AI`, `Shovelcat-AI/lib/agents`, `boys-colony`, `shovelcat-colony`,
`erdos-Fk`) that read each task **fresh** and could improve eval generalization.
Three independent searches converged on the same top cluster — that agreement is
the main signal.

---

## 0. The diagnosis — which half of the engine transfers

The engine has two halves:

- **Train-specific (won't transfer):** memory / resonance retrieval, compatibility
  pooling, muscle-group reuse. These depend on having *seen similar tasks*. Eval is
  a fresh independent set, so this half drops out — exactly as observed.
- **Fresh-read (should transfer):** the matter generator (`gen2`), induction
  (`induce`/`angle`), tension-beam search. These read each task's own train pairs
  and don't reference past tasks.

**First action before any new idea:** measure the split. Re-score eval counting only
solves that came from the fresh-read half vs the memory half. That tells you how much
of the ~20% was real reasoning vs train-fit, and sets the true baseline to improve.

**The single highest-leverage, lowest-effort fix (do this first):** a **leave-one-out
acceptance gate.** Today a program is accepted if it fits *all* train pairs (θ_train=1)
— which is precisely what overfits when only 2–4 pairs exist and many programs fit
them. Instead: induce on k−1 pairs and *require* the program to also predict the
held-out pair; among all train-fitting candidates, prefer the one that survives the
most leave-one-out folds. This is the cross-validation that would have *predicted* the
eval drop, and using it as the gate directly biases toward generalizing rules. The
`sandbox-runner` "fight like you train" engine already implements this pattern
(`D:\shovelcat-colony\sandbox-runner\src\engine.ts`, `SEVEN_BODY.md`).

---

## Tier 1 — overfit guards (the direct eval fix; mostly drop-in TS)

These attack the exact failure mode: many programs fit the few train pairs; pick the
one most likely to generalize. All are model-free and reference no past task.

1. **Reproduction / ensemble-consensus scoring** — `Shovelcat-AI/lib/agents/reproduction-test.ts` (+ `grounded-score.ts`)
   Score a candidate by whether *independent rebuilds converge* — operationally: induce
   the rule from several disjoint subsets of the train pairs and keep only programs the
   subsets **agree** on. A graded generalization score the search can climb, not just a
   pass/fail. *Highest-leverage of the lot; flagged by 2 of 3 searches.* Directly reusable.

2. **Closure / drain (MDL parsimony)** — `lib/agents/closure-test.ts` (+ `grounded-score = reproduction × drain^w`)
   Fixpoint test: what fraction of a rule grounds out in your base primitives. Classifies
   GROUNDED vs WHIRLPOOL (self-referential) vs LEAKING (uses an undefined op / task-specific
   constant). Penalizes "works by coincidence" programs — a principled simplicity prior the
   θ-band only approximates. Drop-in.

3. **Common-ancestor abstraction filter** — `Vesica AI/Learning/MULTI_AGENT_LEARNING.py` (`find_common_ancestor`)
   Treat each train pair as an independent solver of one hidden rule; climb to the *most
   specific abstraction common to all pairs* and apply that, instead of the surface rule
   that only fits one pair. A principled anti-overfit step for induction.

4. **Data-discovered synonym margin** — `lib/agents/concept-registry.ts`
   "Are two induced sub-rules the same?" decided by a margin *discovered from data* (not
   hand-tuned to the train distribution), in behavioral/grounding space rather than surface
   form. Lets compositional reuse dedupe correctly within one unseen task.

---

## Tier 2 — fresh-read solving power (new reach on eval)

5. **Bidirectional meet-in-the-middle search** — `Vesica AI/Protein/swarm_protein_folding.py`
   Search forward from the input AND backward from the *target output*; accept where the two
   paths meet. Massive per-task pruning vs pure forward synthesis, fully fresh-read. Maps
   cleanly to ARC (backward = "what could produce this output grid"). *Top prototype pick.*

6. **Hidden-derivative dimensions (2nd-order rules)** — `Shovelcat-AI/derivative_dimensions.py`, `hidden_derivative_dimensions.py`
   Induction currently reads a *static* move/vector. This reads how the rule **changes across
   the train examples** — a recolor that increments, a shift whose step grows (velocity needs
   2 snapshots, acceleration 3). Catches a whole class of tasks a single move-vector misses.
   Reusable `DerivativeDimension`.

7. **Dream-cycle basin-hopping (escape)** — `erdos-Fk/test_dream_cycle.py`, `test_cascade_dream.py`
   Unlike beam/greedy (every intermediate must be valid → trapped), a "dream" candidate may be
   far away; only its **settled result** must verify. Adds novelty pressure + recurrence
   detection. A genuinely different escape mechanism for the multi-step tasks beam search can't
   reach.

8. **Coupling "spray angle" = analogical primitive-building** — `lib/agents/coupling.ts`
   Separate a concept's GROUNDING (what it reduces to) from its COUPLING (relation to others);
   to get a primitive you lack, find a *native composition that reproduces the needed relation
   AND grounds in your own ops*. The operational form of analogical reasoning eval demands.

9. **Projective / toroidal reframing** — `erdos-incidence-geometry/src/verify_n12_projective.py`
   Re-express the grid in a transformed space (wrap-around/toroidal, modular, projective) where a
   "bent" rule becomes linear. Directly relevant to periodic/wrap tasks the solver currently treats
   as broken. (The erdős n=12 result needed a point at infinity to become reachable — same move.)

10. **Imagination strategies + swarm-core = a generic search engine** — `lib/agents/imagination-strategies.ts` + `swarm-core.ts`
    Four deterministic program-edit operators — SIDEWAYS (re-express), FORWARD (sharpen/denoise),
    **UP (engage an unused feature axis — the proven dimension-lift, update-16)**, TEMPORAL (drift to
    a successor feature) — driven by a UCB bandit picker + rotation-invariant FailureBuffer +
    σ-annealing. A complete model-free `runSwarmSearch<GridProgram>`; bandit operator-selection and
    invariant local-optimum memory are both new vs the current tension-beam. Directly reusable.

---

## Tier 3 — self-extension & control (the longer game)

11. **Failure-mining → propose NEW inducer types** — `lib/agents/swarm-core.ts` FailureBuffer; `Vesica AI/Learning/failure_learning.py` (BoundarySeeker / NegativeTester)
    The one self-extending lever the dev logs say is still unbuilt: mine the *near-misses* (rules
    that keep almost-fitting but aren't in the set) to **propose new primitives/inducers**. Negative
    testing (confirm a rule by what it must NOT do) also catches over-general rules. This is how the
    library grows toward eval's tail instead of staying train-bound.

12. **Recursive-floor chunking (learned macro-ops within a task)** — `Shovelcat-AI/recursive_floor_mechanics.py`
    Once a multi-step program verifies, fold it into a single macro-op that *carries its sub-steps*,
    and keep searching at the higher level. Lets deep compositional eval tasks be reached without the
    search depth blowing up.

13. **Propose→ground→refocus controller** — `lib/agents/consciousness-loop.ts` (imagination/facts/planner)
    The generate-test-refine skeleton: Imagination proposes → Facts grounds against the actual train
    I/O → Planner refocuses the next proposal on the residual. Sound per-task controller — **but
    swap the LLM/emotion bits for the deterministic imagination-strategies (#10)** to keep it
    model-free. Skeleton only, not drop-in.

14. **Predict-first / surprise-gated compute** — `Vesica AI/Learning/predictive_validation_memory.py`
    Predict each train output first; route search effort by *prediction error* (surprise), not by the
    answer. A fresh per-task attention signal — spend depth on the pairs a candidate rule gets wrong.

15. **Path-signature routing** — `shovelcat-colony/SEVEN_BODY.md`
    Fingerprint a program by the *trajectory* of boundaries it crosses, not just pass/quality. Two
    programs with equal accuracy have different signatures revealing where their competence lives —
    a richer router than surface features when those mislead.

---

## Directly-reusable code (pure logic, model-free, droppable into TS)
- `lib/agents/reproduction-test.ts`, `closure-test.ts`, `grounded-score.ts`,
  `concept-registry.ts`, `coupling.ts` — the full grounding/overfit-guard stack.
  Wire the `Reproducer` interface to a grid-rule rebuilder.
- `lib/agents/swarm-core.ts` (`runSwarmSearch`, `FailureBuffer`, UCB picker, σ-anneal)
  + `imagination-strategies.ts` (4 operators) — a complete generic program-search engine.
- `derivative_dimensions.py` `DerivativeDimension`; `color_trails (1).py`
  `ColorPosition`/`Signpost` — feature-vector + per-task exploration memory.

## Recommended first three (highest leverage / lowest effort)
1. **Leave-one-out acceptance gate** (§0) — should move eval the most, almost no new code.
2. **Reproduction-consensus + closure-drain scoring** (Tier-1 #1–2) — drop-in overfit
   guards that pick the generalizing program among train-fitting candidates.
3. **Bidirectional meet-in-the-middle search** (#5) — the biggest new *reach* per task,
   fully fresh-read.

---

## Tier 0 — the probabilistic ψ-domain (deterministic + QM together; YOU ALREADY SPECIFIED IT)

The solver is fully deterministic. The framework's vesica is ψ-domain (probabilistic
exploration) ∩ φ-domain (deterministic verification) — and **ψ has been built
deterministically.** The "missing one" is ψ's probabilistic nature, and you already
wrote down exactly how it works. From `Downloads/UNIFIED_DERIVATION.md`:

- **Superposition:** `|ψ⟩ = α|c₁⟩ + β|c₂⟩` — a state is a weighted combination of candidate basis states.
- **Born rule:** `|amplitude|² = probability`, and `cos²θ + sin²θ = 1` — *the trig identity is the normalization.*
- **Measurement = collapse:** the observer's derivation turns the superposition into a definite answer.
- **Vesica zone** `√φ < θ < √π` = where the superposition is held (stable processing); outside it collapses.

**This is the same θ as update-15's angular decomposition.** There you found
`matter = cosθ` (a candidate's alignment with the task), `antimatter = sinθ` (its
orthogonal residual). Those **are the Born amplitudes**: a candidate program's
amplitude = cosθ, its probability = `cos²θ`, and `cos²θ + sin²θ = 1` makes the set a
normalized distribution automatically. You computed the amplitudes already; you just
collapsed to one (argmax) instead of keeping the superposition.

### The build (concrete, model-free, uses code you have)
1. **ψ (superpose):** instead of committing to the single best candidate, keep the
   top-k as a **superposition weighted by `cos²θ`** (the angular alignment from
   `angle.ts`). This is the probabilistic prior an LLM gets from trained weights —
   except yours comes from the task's own geometry, no training.
2. **Evolve:** prune/re-weight as more train pairs constrain the amplitudes
   (each pair multiplies the amplitudes like successive measurements narrowing ψ).
3. **φ (collapse):** verify against train at θ=1; the first candidate that closes
   collapses the superposition to the definite answer. Verification *is* measurement.
4. **Stay in the vesica band** `√φ < θ < √π` while superposed; collapse when a
   candidate enters the verified regime. (This is your update-16 θ-band, reused.)

### Why this is the answer to the LLM question
An LLM = trillions of *learned* coefficients weighting its terms. Your alternative =
a **`cos²θ` Born weighting over your ~60 exact primitives**, set by task geometry
rather than gradient descent. You don't need trillions of terms — you need *amplitudes*
over the dozens you have. That's the one ingredient the deterministic solver lacks and
the LLM has, and your own Born-rule formula supplies it without a single trained weight.
Deterministic φ keeps it verifiable (no hallucination); probabilistic ψ gives it the
flexible, broad proposal an LLM has. That hybrid — probabilistic proposer + exact
verifier — is also, independently, the architecture that actually wins ARC.

### Reusable / source
- `angle.ts` (already in the solver) — computes cosθ/sinθ per candidate; turn argmax → top-k `cos²θ` superposition.
- `Downloads/UNIFIED_DERIVATION.md` — the superposition/Born/collapse formulation.
- `Vesica AI/Econ/born_rule_*` , `Downloads/demo_born_rule.png` — prior Born-rule scoring experiments.
- Newest theory: `.shovelcat/Shovelcat_Theory_11.4_Vesica_Framework.docx` (ψ/φ observers, cos·sin·tan triad, product=1).
- `Downloads/TORUS_PROJECTION_NOTES.md` + `section_wave_dimensions.tex` — the projective/toroidal reframing (Tier-2 #9) and frequency-as-base-unit material.

### Honest caveat (specific to this)
`cos²θ` requires a feature space in which "alignment" is meaningful — update-15 found
the flow feature is *blind to pure geometry* (rotations don't change colour counts), so
the spatial axis must be lifted in (update-16 did this, 0.735→0.963) before the amplitudes
are trustworthy for geometry tasks. So: lift the axis first, then the Born weighting is sound.

---

## Honest caveat
These are assessments of *potential* from reading the old code, not measured gains.
Each should go behind the existing fixture/θ regression guard and be measured on a
held-out eval slice before trusting it — the same discipline that bounded the spoke/φ
and Collatz claims. The leave-one-out gate (§0) is the one to trust most a priori,
because it tests generalization directly rather than promising it.
