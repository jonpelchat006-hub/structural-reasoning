# ARC-AGI-1: the model-free solver

Source for thread 1 of the top-level README: an ARC-AGI-1 solver with no language model anywhere.

- **`arc-slice/`** is the base solver: the ARC loader, the grid type, a small DSL, candidate programs, an
  exact-match verifier and the search (`src/`). Its numbers are in `arc-slice/RESULTS.md`; `out*.log` are the
  saved outputs of the runs; `verified_*.txt` list the verified solves. `arc-slice/slotfill/` is a separate
  verified slot filler for same-size tasks (Oct 2026); see its README.
- **`arc-proposer/`** is the layer built on top of it (signatures, memory, induction, the "bender").
  `arc-proposer/src/` imports from `../../arc-slice/src/`, so the two folders must stay side by side. The
  analysis write-ups for this layer are in [`../theory/framework/`](../theory/framework/) (RESULTS.md,
  ISOLATION_TEST.md, TRUST_AUDIT_RESULTS.md, SPARSE_VESICA_EXPANSION.md and the others).

**Not included:** the ARC task files. The solver reads the 400 public training tasks from `arc-slice/data/`
and the evaluation tasks from `arc-slice/data-eval/`; get them from <https://github.com/fchollet/ARC-AGI>.
The scripts are TypeScript run with `tsx` (see `arc-slice/package.json`).

**Status:** measured. The headline number is 66/400 (16.5%) on public training, every solve checked on the
held-out test pair; the write-ups say plainly that this is not competitive with the top of the leaderboard.

## Files

**`arc-proposer/`**

- [`LLM_EQUATION_MAP.md`](arc-proposer/LLM_EQUATION_MAP.md) — The LLM Equation, Mapped Outward
- [`anchor_test.py`](arc-proposer/anchor_test.py) — For each UNSOLVED task: distance to nearest SOLVED task (the anchor it could build from)
- [`iso_analysis.py`](arc-proposer/iso_analysis.py) — isolation = distance to nearest OTHER task

**`arc-proposer/src/`**

- [`bender.ts`](arc-proposer/src/bender.ts) — bender.ts — the tension-directed beam bender. No model. Tension = distance from
- [`complete.ts`](arc-proposer/src/complete.ts) — complete.ts — the GENERATOR pole (sphere "tail"): the new content is FORCED by
- [`coordinator.ts`](arc-proposer/src/coordinator.ts) — coordinator.ts — the non-LLM coordinator. Construct/Deconstruct/Plan over the
- [`induce.ts`](arc-proposer/src/induce.ts) — induce.ts — operator INDUCTION. Don't enumerate the move; READ it from the
- [`induce2.ts`](arc-proposer/src/induce2.ts) — induce2.ts — more induction templates. Each induces its PARAMETER from the
- [`memory.ts`](arc-proposer/src/memory.ts) — carve on a landing: bank a solved task's signature -> family (gated, not every bounce).
- [`repgap.ts`](arc-proposer/src/repgap.ts) — repgap.ts — representation-gap diagnostic. For each task classify WHAT its
- [`run_isolation.ts`](arc-proposer/src/run_isolation.ts)
- [`runbender.ts`](arc-proposer/src/runbender.ts)
- [`runcoarse.ts`](arc-proposer/src/runcoarse.ts) — runcoarse.ts — 4-probe coarse map (4→16→64). Probe each task with the 4
- [`runcollapse.ts`](arc-proposer/src/runcollapse.ts) — runcollapse.ts — THE compounding test. Floor-collapse: each solved composition
- [`runcomplete.ts`](arc-proposer/src/runcomplete.ts)
- [`runcoord.ts`](arc-proposer/src/runcoord.ts)
- [`runinduce.ts`](arc-proposer/src/runinduce.ts)
- [`runinduce2.ts`](arc-proposer/src/runinduce2.ts)
- [`runmem.ts`](arc-proposer/src/runmem.ts) — runmem.ts — leave-one-out recall: would the memory point us at the right
- [`runpool.ts`](arc-proposer/src/runpool.ts) — runpool.ts — compatibility pooling. Route each task by features to a small
- [`runrepgap.ts`](arc-proposer/src/runrepgap.ts)
- [`runseam.ts`](arc-proposer/src/runseam.ts) — runseam.ts — full stack + seam-typed repair; report new solves + seam histogram.
- [`runsig.ts`](arc-proposer/src/runsig.ts) — family label = the kind of solution (primary op / codon), or null
- [`runtax.ts`](arc-proposer/src/runtax.ts) — runtax.ts — muscle taxonomy. Which muscle groups do we HAVE (families in solved
- [`runtier.ts`](arc-proposer/src/runtier.ts) — runtier.ts — impact-tiered pools (4→16→64 by tiles affected). Classify each op
- [`runtwin.ts`](arc-proposer/src/runtwin.ts) — runtwin.ts — twin-anchor transfer (ISOLATION_TEST lever). Lift each SOLVED
- [`seam.ts`](arc-proposer/src/seam.ts) — seam.ts — classify_seam_profile ported to grids. Read the SHAPE of the diff
- [`signature.ts`](arc-proposer/src/signature.ts) — signature.ts — encode an ARC task as a point in Jonathan's 7D colour space

**`arc-slice/`**

- [`RESULTS.md`](arc-slice/RESULTS.md) — ARC-AGI-1 baseline slice — results
- [`chk.ts`](arc-slice/chk.ts)
- [`dbg.ts`](arc-slice/dbg.ts)
- [`eval_schema_map.py`](arc-slice/eval_schema_map.py)
- [`lift_axis.py`](arc-slice/lift_axis.py)
- [`run8.ts`](arc-slice/run8.ts) — run8.ts — isolate the bug-finder: brute1 (exact) + single-op repair pass, no swarm.
- [`structure_meter.py`](arc-slice/structure_meter.py) — structure_meter — RH-distance as a structure/routing signal for ARC grids.
- [`valid.ts`](arc-slice/valid.ts) — 1) MECHANISM TEST: take a brute1-solved task, deliberately corrupt the program's

**`arc-slice/slotfill/`**

- [`arc_levels.py`](arc-slice/slotfill/arc_levels.py) — Sort ARC tasks by the frame's levels and compare with what the solver already solves (read-only).
- [`diag.py`](arc-slice/slotfill/diag.py)
- [`evaluate.py`](arc-slice/slotfill/evaluate.py) — Measure the slot filler on ARC-1 train and eval: per class, attempted / correct@1 / correct@2 / wrong,
- [`export.py`](arc-slice/slotfill/export.py) — Write the slot filler's answers for every task it commits to: slotfill_predictions.json.
- [`show.py`](arc-slice/slotfill/show.py)
- [`slotfill.py`](arc-slice/slotfill/slotfill.py) — Slot filler for ARC tasks whose outputs only fill background cells.

**`arc-slice/src/`**

- [`_diag.ts`](arc-slice/src/_diag.ts) — does object multiset (shape+color) survive but positions change? = a move task
- [`_gmtest.ts`](arc-slice/src/_gmtest.ts) — reuse learnMove by importing the module's function isn't exported; re-run its logic inline is heavy.
- [`ability_draft.ts`](arc-slice/src/ability_draft.ts) — ability_draft.ts — §13.4: wire the ABILITY-DRAFT into the solver.
- [`angle.ts`](arc-slice/src/angle.ts) — angle.ts — test the ANGULAR matter/antimatter decomposition.
- [`antimatter.ts`](arc-slice/src/antimatter.ts) — antimatter.ts — the EXTRACTION sphere (mirror of gen2's generation sphere).
- [`atomchem.ts`](arc-slice/src/atomchem.ts) — atomchem.ts — "know what an atom IS": characterize each op like an element.
- [`audit.ts`](arc-slice/src/audit.ts) — audit.ts — replicate every imported OP "in our own words".
- [`bidir.ts`](arc-slice/src/bidir.ts) — bidir.ts — BIDIRECTIONAL meet-in-the-middle. Program P: input->output split as
- [`blindeval.ts`](arc-slice/src/blindeval.ts) — blindeval.ts — HONEST blind-submission eval. No peeking at test. Per task, collect
- [`bounce_scan.ts`](arc-slice/src/bounce_scan.ts) — bounce_scan.ts — §16: the DOUBLE-BOUNCE roof search. A COMPOSITIONAL program search that JUMPS
- [`budget.ts`](arc-slice/src/budget.ts) — budget.ts — §28: CONSERVATION OF DUST. Searches produce a FINITE amount of each ingredient; you cannot
- [`bugfinder.ts`](arc-slice/src/bugfinder.ts) — If one consistent colour mapping makes every dims-matching pair exact, return prog + a cmap op that applies it. Catches "shape ri…
- [`channel.ts`](arc-slice/src/channel.ts) — channel.ts — §27: the DARK-MATTER CHANNELING CYCLE. The memory layer is the OBSERVER/router that decides
- [`closer2_scan.ts`](arc-slice/src/closer2_scan.ts) — closer2_scan.ts — §18.10 the CLOSURE-EQUATION CLOSER, with the §18.11–18.13 refinements.
- [`closer_scan.ts`](arc-slice/src/closer_scan.ts) — closer_scan.ts — §18.9: the residual-CLOSER as a learned ENERGY-TRANSFER ORIENTATION. The triangulated
- [`codon.ts`](arc-slice/src/codon.ts) — codon.ts — the operator generator. A codon = (selector × action), the
- [`colorbij_scan.ts`](arc-slice/src/colorbij_scan.ts) — colorbij_scan.ts — §47: THE BIJECTION ATOM (Jonathan). A colour map that is a BIJECTION carries its own
- [`composeSpheres.ts`](arc-slice/src/composeSpheres.ts) — composeSpheres.ts — the VESICA: matter ∘ antimatter (two spheres overlapping).
- [`contract_scan.ts`](arc-slice/src/contract_scan.ts) — contract_scan.ts — §33: EXPAND-then-CONTRACT with per-atom coordinate descent (Jonathan).
- [`cycle.ts`](arc-slice/src/cycle.ts) — cycle.ts — the MATTER/ANTIMATTER CYCLE. Antimatter proposes a CONSTRAINT region
- [`cycles.ts`](arc-slice/src/cycles.ts) — cycles.ts — §29: the CLOSED-CYCLE MAP EXPANDER. Not a solver — a REACHABILITY explorer. Jonathan: before
- [`deposition.ts`](arc-slice/src/deposition.ts) — deposition.ts — §25: AFFINITY-SORTED LAYERING on the memory's lines (grounded in Vesica Physics).
- [`derivprobe.ts`](arc-slice/src/derivprobe.ts)
- [`discover.ts`](arc-slice/src/discover.ts) — discover.ts — the generator RECEIVES an element (native prefix op1, "placed where it
- [`dna_biased_scan.ts`](arc-slice/src/dna_biased_scan.ts) — dna_biased_scan.ts — §30: THE PAYOFF TEST. Does seeding the solver from the §29 middle-shell reaction
- [`dna_scan.ts`](arc-slice/src/dna_scan.ts) — dna_scan.ts — §19: the DNA rung. A solution is a GENOME (op sequence) written in a 64-codon code
- [`dna_suffix_scan.ts`](arc-slice/src/dna_suffix_scan.ts) — dna_suffix_scan.ts — §19.6 fix: SEMI-CONSERVATIVE replication check on the INVERTIBLE SUFFIX only.
- [`dprobe2.ts`](arc-slice/src/dprobe2.ts)
- [`draw2.ts`](arc-slice/src/draw2.ts) — draw2.ts — "our own version of drawing": a per-task LEARNED draw decoder.
- [`dsl.ts`](arc-slice/src/dsl.ts) — dsl.ts — the operator vocabulary (the "moves" the search composes).
- [`dust_scan.ts`](arc-slice/src/dust_scan.ts) — dust_scan.ts — §42: the TOROIDAL RETURN (Jonathan). Ascent climbs the inner shells shedding DUST
- [`flowmap.ts`](arc-slice/src/flowmap.ts) — flowmap.ts — classify every task by its MATTER(+)/ANTIMATTER(-)/VOID(0) flow.
- [`fold_flat_scan.ts`](arc-slice/src/fold_flat_scan.ts) — fold_flat_scan.ts — §45: FLATTEN ONE SIDE, THE OTHER COMPLETES THE CYCLE (Jonathan). Bounce = flatten
- [`fold_scan.ts`](arc-slice/src/fold_scan.ts) — fold_scan.ts — §32: the OUTER-SHELL FOLDING SOLVER with the BALANCE acceptance rule (§31).
- [`frustration.ts`](arc-slice/src/frustration.ts) — Golden-ratio additive recurrence in [0,1): low-discrepancy, deterministic.
- [`gen2.ts`](arc-slice/src/gen2.ts) — gen2.ts — SELF-SYNTHESIZING generator built from our own generative ATOMS.
- [`gen2cmp.ts`](arc-slice/src/gen2cmp.ts)
- [`generator.ts`](arc-slice/src/generator.ts) — generator.ts — PARAMETRIC INDUCED generator for INK_ADDED tasks.
- [`genfixture.ts`](arc-slice/src/genfixture.ts) — re-expose internals by re-running each template via a tagged inducer
- [`gentest.ts`](arc-slice/src/gentest.ts)
- [`geomove_scan.ts`](arc-slice/src/geomove_scan.ts) — geomove_scan.ts — §50: PER-OBJECT GEOMETRY (Jonathan). §49's vortex machinery pointed at POSITION, not
- [`geostack_scan.ts`](arc-slice/src/geostack_scan.ts) — geostack_scan.ts — §51: THE MINIMAL RING — coupled object motion by dependency ORDER (Jonathan). §50's
- [`grid.ts`](arc-slice/src/grid.ts) — Fraction of cells that match, only meaningful when dims are equal.
- [`isnt.ts`](arc-slice/src/isnt.ts) — isnt.ts — the ANTIMATTER GENERATOR: makes "isn't" tags. Where gen2 asserts what a
- [`isntdiag.ts`](arc-slice/src/isntdiag.ts)
- [`isotope_scan.ts`](arc-slice/src/isotope_scan.ts) — isotope_scan.ts — §18.19: the VOID PERIODIC TABLE. Every train-closing closure map is a SYNTHESIZED
- [`jet.ts`](arc-slice/src/jet.ts) — jet.ts — FORCE-CANCELLATION beam search. Residual = the unknown force the game
- [`jetverify.ts`](arc-slice/src/jetverify.ts)
- [`kerneltier.ts`](arc-slice/src/kerneltier.ts) — kerneltier.ts — the "kernel tier": Lean-Kernel-Challenge-style gates for ARC rules.
- [`knot_scan.ts`](arc-slice/src/knot_scan.ts) — knot_scan.ts — §37/§38: the KNOT LADDER (Jonathan). Two sheets folding at the edge tie into a KNOT; the
- [`lateral_scan.ts`](arc-slice/src/lateral_scan.ts) — lateral_scan.ts — §18.7: the Shark needs a compass. Anchor it at a KNOWN BRANCH already further out
- [`learn.ts`](arc-slice/src/learn.ts) — learn.ts — META-LEARN priors (ComponentLibrary style): which INDUCER solves which
- [`learnedeval.ts`](arc-slice/src/learnedeval.ts) — learnedeval.ts — eval WITH learned priors. Per task: pick the inducer order from the
- [`loader.ts`](arc-slice/src/loader.ts) — loader.ts — read ARC task JSON from data/.
- [`looeval.ts`](arc-slice/src/looeval.ts) — still try light stages
- [`molecule_scan.ts`](arc-slice/src/molecule_scan.ts) — molecule_scan.ts — §17: a program is a MOLECULE; some tasks need TWO atoms BONDED, not one longer
- [`morph.ts`](arc-slice/src/morph.ts) — structural skeleton key — ignores literal colors, so different-coloured solutions of the same shape collapse to one template (the…
- [`multistrand_scan.ts`](arc-slice/src/multistrand_scan.ts) — multistrand_scan.ts — §19.8: MORE THAN TWO STRANDS. A "strand" = an independent derivation that
- [`nested.ts`](arc-slice/src/nested.ts) — nested.ts — depth-bounded recursive synthesis (the seven-body fractal interior).
- [`objects.ts`](arc-slice/src/objects.ts) — 4-connected components. mode "color": same-color blobs; "blob": any non-bg connected.
- [`ops-batch2.ts`](arc-slice/src/ops-batch2.ts) — anti-diagonal transpose (the D4 element not directly named)
- [`ops-combinator.ts`](arc-slice/src/ops-combinator.ts) — sub-grid covering an object's bbox (cells off the object set to -1).
- [`ops-count.ts`](arc-slice/src/ops-count.ts) — ops-count.ts — count / shape-class / flood primitives (inner-shell muscle).
- [`ops-fractal.ts`](arc-slice/src/ops-fractal.ts) — ops-fractal.ts — self-similar tiling (the classic ARC fractal pattern).
- [`ops-generate.ts`](arc-slice/src/ops-generate.ts) — ops-generate.ts — the GENERATOR's first organ: create new content (the 6%
- [`ops-move.ts`](arc-slice/src/ops-move.ts) — ops-move.ts — object-movement muscle (the #1 missing group per the taxonomy).
- [`ops-muscle.ts`](arc-slice/src/ops-muscle.ts) — ops-muscle.ts — high-value ARC primitive families ("muscle groups"). Bending
- [`ops-object.ts`](arc-slice/src/ops-object.ts) — ops-object.ts — object-level transforms. Each returns Grid/null.
- [`ops-panel.ts`](arc-slice/src/ops-panel.ts) — ops-panel.ts — sub-grid / panel primitives (inner-shell muscle). Many ARC tasks
- [`ops-relate2.ts`](arc-slice/src/ops-relate2.ts) — ops-relate2.ts — object-level relations + diagonal symmetry completion.
- [`ops-relational.ts`](arc-slice/src/ops-relational.ts) — recolour each object by its SIZE rank (1,2,3,...). A downstream cmap maps ranks -> the task's actual colours, so "recolour by siz…
- [`ops-shape.ts`](arc-slice/src/ops-shape.ts) — ops-shape.ts — shape-transform primitives (boundary / interior).
- [`orbital_scan.ts`](arc-slice/src/orbital_scan.ts) — orbital_scan.ts — §34/§35: the ORBITAL / CONTINUOUS-PARAMETER closer (the quantum state).
- [`perobject_scan.ts`](arc-slice/src/perobject_scan.ts) — perobject_scan.ts — §48: THE PER-OBJECT MAP via the SPIRAL WINDOW (Jonathan). The one lever five
- [`poly_scan.ts`](arc-slice/src/poly_scan.ts) — poly_scan.ts — §39: the POLYNOMIAL LADDER (Jonathan). Floor number = polynomial order (the §1 expansion
- [`probe_b2.ts`](arc-slice/src/probe_b2.ts)
- [`prof.ts`](arc-slice/src/prof.ts)
- [`prof2.ts`](arc-slice/src/prof2.ts)
- [`program.ts`](arc-slice/src/program.ts) — Run the whole pipeline; null if any stage is illegal.
- [`prune.ts`](arc-slice/src/prune.ts) — prune.ts — the PRUNE-DOWN direction (top-down from the possibility space, not built up from
- [`qtransform.ts`](arc-slice/src/qtransform.ts) — rotation r*90 about z as a unit quaternion (half-angle r*45deg).
- [`quaternion.ts`](arc-slice/src/quaternion.ts) — Hamilton product — ij = k, ji = -k
- [`relations.ts`](arc-slice/src/relations.ts) — detect relations that hold across EVERY training pair (invariants).
- [`relfreq.ts`](arc-slice/src/relfreq.ts)
- [`role_closure_scan.ts`](arc-slice/src/role_closure_scan.ts) — role_closure_scan.ts — §20.6: the CONSCIOUSNESS-LOOP closure as the acceptance gate.
- [`roof.ts`](arc-slice/src/roof.ts) — roof.ts — the FIRST ROOF tool (per-task synthesizer, the dream/imagination layer).
- [`run.ts`](arc-slice/src/run.ts) — run.ts — end-to-end baseline: load -> brute depth-1 -> swarm restarts -> verify.
- [`run10.ts`](arc-slice/src/run10.ts) — run10.ts — isolate the NEW combinators' contribution (with bug-finder).
- [`run11.ts`](arc-slice/src/run11.ts) — run11.ts — unified DETERMINISTIC pipeline (no swarm), deduplicated.
- [`run2.ts`](arc-slice/src/run2.ts) — run2.ts — roof + frustration pipeline, with A/B vs the plain baseline.
- [`run4.ts`](arc-slice/src/run4.ts) — run4.ts — morph (corkscrew) experiment.
- [`run5.ts`](arc-slice/src/run5.ts) — run5.ts — distinguish genuine cross-task TRANSFER from self-recall.
- [`run6.ts`](arc-slice/src/run6.ts) — run6.ts — rigorous leave-one-out transfer test, now TRANSFORM-AWARE.
- [`run7.ts`](arc-slice/src/run7.ts) — run7.ts — measure the bug-finder's contribution.
- [`run8.ts`](arc-slice/src/run8.ts) — run8.ts — isolate the bug-finder: brute1 (exact) + single-op repair pass, no swarm.
- [`run9.ts`](arc-slice/src/run9.ts) — run8.ts — isolate the bug-finder: brute1 (exact) + single-op repair pass, no swarm.
- [`runall.ts`](arc-slice/src/runall.ts) — still try light stages
- [`runanti.ts`](arc-slice/src/runanti.ts)
- [`runcodon.ts`](arc-slice/src/runcodon.ts) — counted optimistically below via re-derive
- [`rundump.ts`](arc-slice/src/rundump.ts)
- [`runeval.ts`](arc-slice/src/runeval.ts) — still try light stages
- [`runfast.ts`](arc-slice/src/runfast.ts)
- [`rungen.ts`](arc-slice/src/rungen.ts)
- [`rungen_eval.ts`](arc-slice/src/rungen_eval.ts) — rungen_eval.ts — run the discovery engine (with the leave-one-out gate) over the EVAL set,
- [`runisnt.ts`](arc-slice/src/runisnt.ts)
- [`runnested.ts`](arc-slice/src/runnested.ts)
- [`scan_map.ts`](arc-slice/src/scan_map.ts) — scan_map.ts — §21/§22/§23/§24: SCAN MAP as pure REPLAY of the live event log, grounded in Vesica Physics.
- [`scan_recorder.ts`](arc-slice/src/scan_recorder.ts) — scan_recorder.ts — §22.5/§23.3: LIVE recording. Every scan calls rec(...) as it runs; each call appends
- [`search.ts`](arc-slice/src/search.ts) — search.ts — wire the REAL swarm-core engine to ARC program search.
- [`solvent_scan.ts`](arc-slice/src/solvent_scan.ts) — solvent_scan.ts — §46: THE SOLVENT QUATERNION (Jonathan + Double_Bounce). Water is two things = the two
- [`species.ts`](arc-slice/src/species.ts) — species.ts — §26: SPECIES = solving genomes (§19 DNA); do they reflect the "planet composition"?
- [`spray_scan.ts`](arc-slice/src/spray_scan.ts) — spray_scan.ts — §41: SPRAY HOTSPOTS (Jonathan, §39c). Floor 1's outer shell sprays energy upward at
- [`spring_scan.ts`](arc-slice/src/spring_scan.ts) — spring_scan.ts — §16b: the SECOND bounce. Run depth-3; for the springs that poke furthest into the
- [`swarm-core.ts`](arc-slice/src/swarm-core.ts) — SWARM CORE — Shared primitives for the nested-swarm search ============================================================ Pure logi…
- [`swarm_scan.ts`](arc-slice/src/swarm_scan.ts) — swarm_scan.ts — §18.3 the DOUBLE BOUNCE = bidirectional meet-in-the-middle, ported from Jonathan's
- [`tank2_scan.ts`](arc-slice/src/tank2_scan.ts) — tank2_scan.ts — §44: FILLING THE SECOND LAKE (Jonathan). The descending sheet's atoms carry a VOID
- [`tank_scan.ts`](arc-slice/src/tank_scan.ts) — tank_scan.ts — §43: TWO LAKES / TAN-FLIP MEET (Jonathan). The torus has two sheets: the ascending
- [`theta.ts`](arc-slice/src/theta.ts) — theta.ts — measure the OVERLAP equilibrium θ on held-out test.
- [`topo.ts`](arc-slice/src/topo.ts) — topo.ts — the TOPOLOGY lift: inducers keyed on holes / enclosure (the axis eval lives in,
- [`trace.ts`](arc-slice/src/trace.ts) — trace.ts — v1 of the TRACE SYNTHESIZER, the ARC distillation of the geo format:
- [`transfer.ts`](arc-slice/src/transfer.ts) — All concrete programs for a shape, bounded so multi-op shapes don't explode.
- [`trust_audit.ts`](arc-slice/src/trust_audit.ts) — trust_audit.ts — a TRUST SYSTEM for the inner shell (Jonathan's trust-economy applied to
- [`valencecompose.ts`](arc-slice/src/valencecompose.ts) — valencecompose.ts — bond atoms by VALENCE (knot/tail chemistry). A task demands
- [`verify.ts`](arc-slice/src/verify.ts) — Smooth score in [0,1] for the search to climb (1.0 only if every pair is exact).
- [`vesica.ts`](arc-slice/src/vesica.ts) — vesica.ts — the Sparse Vesica Expansion superposition (cos²θ Born + antimatter setups).
- [`vortex_scan.ts`](arc-slice/src/vortex_scan.ts) — vortex_scan.ts — §49: THE VORTEX / OCTONION PER-OBJECT FUNCTION (Jonathan). §48 read INTRINSIC features
