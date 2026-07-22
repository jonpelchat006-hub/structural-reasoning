# The Void Line

### An interface-centered, multi-scale reading of two-domain protein architecture — and its recurring convergence motif

**Working draft / idea record.** Author: Jonathan *[surname, affiliation to be completed]*.
Computational tests performed collaboratively with an AI assistant (Claude); all structural
analyses are reproducible from the scripts named in the Appendix.

*Status: this is an exploratory working paper — a record of ideas and the small-scale
computational tests used to check them. It is not peer-reviewed, and it is not a claim of a
predictive advance. Its value is (a) a set of internally consistent geometric descriptions of
two-domain interfaces, confirmed on a small curated set; (b) a single organizing motif that recurs
across scales; and (c) a demonstration that the one hard limit these descriptions run into — the
"wall" — can be climbed with an off-the-shelf protein language model, cheaply. Every result is
tagged CONFIRMED, DEMONSTRATED, ESTABLISHED (imported science), ANALOGY, OPEN, or NEGATIVE. Read the
honest ledger (§12) first if you want the one-page version.*

---

## 1. Abstract

We take a single object — the **void line**, the interdomain seam where two domains of a protein
meet — as the organizing center of a two-domain fold, and ask a series of geometric questions about
it. Working from physical intuitions and testing each on a small curated set of eight two-domain
enzymes (with additional ligand-bound and conformational-pair structures), we find a coherent
picture: the void line is simultaneously the **active-site pocket**, the **rotation axis** of the
domain-closure motion, a **charge-complementary register**, and a **continuous cut surface** that
the single chain threads 1–7 times. The chain's crossings of this surface obey a **continuity
conservation law** (signed crossings cancel to within ±1 from every viewing angle). The interface,
treated as a graded field ("C"), forms a single connected **trail** centered on the seam whose
convergence point coincides with the bound cofactor ("D"); folding is shown to *create* this seam
rather than to eliminate it. The whole structure is **recursive**: bisecting repeatedly produces a
new interface at every scale, and the deepest convergence of these nested interfaces is the
catalytic center. We connect the buried, funnel-shaped catalytic pocket to the general architecture
of biological **readers** (photoreceptors and other GPCRs), where a chromophore in a shielded pocket
transduces an input at a converging apex — the same convergence motif, one scale up. Throughout, a
persistent **wall** appears: local/sequence information *describes* the interface but does not
*predict* its global layout. We then **climb the wall**: an off-the-shelf protein language model
(ESM-2), given sequence only, predicts a contact web from which the seam is recovered at 82–94%
agreement with the true structural seam — and this works with the *smallest* available model and
only ~0.2×L of the predicted contacts, giving a concrete recipe for running the analysis on modest
hardware. Recovering global structure is thus a matter of wrapping the structural "inside" with a
learned outer layer, whose agreement across observers is the invariant and whose disagreement
encodes depth. We are explicit throughout about what is measured, what is imported established
science, what is analogy, and what remains open.

---

## 2. Preface — what this is and is not

This paper grew from a long dialogue in which one author proposed geometric and physical intuitions
about how proteins fold and "read," and each intuition was turned into a concrete computational test
on real protein coordinates. The method throughout was: **state the intuition, operationalize it,
run it, and report the honest verdict — including the failures.** Two intuitions were refuted
outright and are reported as such; several "confirmations" carry important caveats; several
appealing ideas are only analogies across domains and are labeled that way; and a few strands that
began from fringe or pseudoscientific material (pyramid "energy," strong claims about biophoton
"communication") are explicitly bounded to the parts that survive contact with real physics.

The dataset is **small** (eight curated single-chain two-domain enzymes), and the domain boundary
is located by a **spectral (Fiedler) bisection** of the residue contact graph, used as a fast proxy
for a proper minimum-cut. Results are therefore best read as **descriptions that are internally
consistent and reproducible**, not as population-level claims. Where a result coincides with
well-established biochemistry (active sites in interdomain clefts, induced fit, the hydrophobic
effect, GPCR signal transduction, single-photon vision), we say so and lean on that literature
rather than on our sample. The one place we make a forward-looking *methodological* claim — that the
wall can be climbed with a protein language model — we back with a live demonstration (§11), while
still flagging its small scale.

---

## 3. Introduction

A two-domain enzyme has an obvious but under-exploited feature: the **seam** between its two
domains. This paper treats that seam — which we call the **void line**, following the intuition that
it is where the two domains' "presence fields" cancel — as the organizing object of the whole fold,
and asks what can be learned by looking at everything *through* it.

The guiding intuitions, in the order they were pursued, were roughly: the seam is a knife-cut
through the structure; it is also the ligand pocket; the two faces are complementary like a
lock-and-key or like base pairs; the chain threads it; folding pivots around it; the interface is a
graded "quality" that forms a trail; the trail converges to a point where the cofactor sits;
reading/transduction happens at that converging point; and the same converging-reader shows up in
eyes and, more generally, in the receptor machinery biology uses for every sense. Each of these was
tested. The through-line that emerged, and that we think is the real contribution, is a **single
convergence motif seen at every scale** — helix, motif, domain, fold, organ — together with a
recurring epistemic limit (the "wall") that separates what a local reader can confirm from what only
a nonlocal outer layer (a language model, or a committee of observers) can recover.

---

## 4. Methods

**Structures.** Coordinates were fetched from the RCSB PDB (BinaryCIF, first model, first chain
unless noted). The core two-domain set: **1CLL** (calmodulin), **3PGK** and **1PHP**
(phosphoglycerate kinases), **1GD1** (GAPDH), **6LDH** (lactate dehydrogenase), **8TLN**
(thermolysin), **4AKE**/**1AKE** (adenylate kinase, open/closed), **2LZM** (T4 lysozyme).
Ligand-bound structures used for pocket analyses: 1AKE (AP5A), 1GD1 (NAD), 2CTS (CoA), 1B8A (ATP),
2YHX, 1PHP (ADP). Rhodopsin **1U19** (11-cis retinal) for the reader analysis.

**Domain partition.** The residue Cα contact graph (edge if Cα–Cα < 8 Å) was split by the sign of
the second eigenvector (Fiedler vector) of its normalized Laplacian, giving faces A and B. This is a
proxy for the established minimum-cut interdomain boundary; it is fast and reproducible but coarser
than a curated boundary, and it mis-splits genuine 3+-domain proteins.

**Interface field ("mixedness").** For each residue, a distance-weighted fraction of nearby residues
belonging to the *other* face (Gaussian weight, σ = 8 Å), giving a graded interface quality in
[0, ~0.5], zero deep in a domain and maximal at the seam.

**Language-model web.** Contact maps were predicted from sequence alone using ESM-2 (8M and 35M
parameter models, `fair-esm`, CPU) via the unsupervised contact head; the predicted web was then
bisected identically to the true web.

**Other measures.** Solvent accessibility via biotite `sasa` (relative to Tien 2013 maxima);
hydropathy via Kyte–Doolittle; secondary structure via biotite `annotate_sse`; rigid-body motions
via Kabsch superposition and screw-axis extraction; signed void-line crossings via hysteresis
thresholding of the backbone projected on the cut normal; pocket geometry via ray-casting from the
ligand apex. Nulls used label permutation (charge signs) or random projection axes. Full parameters
are in the per-test scripts (Appendix).

**Verdict protocol.** Each intuition was assigned CONFIRMED (measured, with caveats), DEMONSTRATED
(a working proof-of-concept pipeline), or NEGATIVE (refuted); where the claim was about imported
science or cross-domain mapping, ESTABLISHED or ANALOGY. "Confirmed" never means more than "holds on
this set with the stated method."

---

## 5. Results I — the seam as architecture

**The ligand sits on the void line, reached from both borders (CONFIRMED, small n).** Across a
curated ligand-bound set the bound cofactor lies on or near the cut plane and is contacted from both
domains in the closed state; open-form structures are caught contacting one domain only. The
interdomain seam *is* the active site — consistent with textbook enzymology (active sites in
interdomain clefts).

**The chain knits through the seam 1–7 times (CONFIRMED).** Counting backbone crossings of the cut
plane, every protein has one dominant two-domain partition (woven at the large scale) that the
single chain threads back through 1–7 times (calmodulin 1, LDH 7). Knit and weave are the same chain
at two scales.

**The two faces are a complementary charge register — the "matching slot" (CONFIRMED, small n).**
Cross-seam charged contacts are opposite-sign (salt bridges) far more than chance at true rivet
distance: **81% opposite-sign at 4.5 Å, Stouffer z = 2.70**, decaying to ~60% (chance) by 8 Å. The
matched slots are the buried rivets; the loose zone is incidental. One protein (thermolysin, a
metal-cluster protease) inverts the rule. The two faces carry a small, static charge separation (a
standing "voltage"), but the interior core is held by **shape** complementarity, not by salt and not
by hydrophobicity (see §8).

**A ~15% irreducibly-mixed woven core (CONFIRMED).** Winner-take-all cleanup of the fuzzy interface
resolves ~85% of it into crisp A/B/void, leaving a ~15% core where the two domains genuinely
interpenetrate — matching, independently, the ~13% floor a series of cuts cannot remove. This core
is the physical "wall": local operations cannot separate it.

---

## 6. Results II — the seam as axle, and the closed state

**Reading is not "one side at a time" (NEGATIVE).** The intuition that the register is read one
strand at a time predicts an antiparallel or exposure-asymmetric seam. Neither holds: the two faces
are **43% antiparallel** (identical to ordinary intradomain packing, p = 0.25) and their exposures
are **positively** correlated (both buried or both exposed together; 40% both-exposed). The register
is **symmetric** — a palindrome-like complementary pairing, not a polar template. This bounds how
far the DNA analogy reaches: complementarity yes, read-polarity no.

**Block-and-rotate: the void line is the axle (CONFIRMED, strong).** Using adenylate kinase caught
open (4AKE) and closed (1AKE), pinning the CORE domain leaves it nearly fixed (1.3 Å) while the LID
swings **14 Å** and the NMP domain **10 Å** to close on the ligand. The **screw axis** of that
rotation sits **2–5 Å from the seam** — the void line is literally the hinge. "Reading" is the
closure *event*, not a scan. During closure **~24% of the contact web forms/breaks** (74 form, 48
break) — the web is not a fixed scaffold.

**The trail is two-sided and meets when the enzyme closes (CONFIRMED).** Split by domain, each
side's interface trail spans ~half the structure; for compact/closed enzymes the two spans sum
> 1.0 and overlap in the middle (the woven core), while the two open-form kinases and calmodulin do
not reach overlap. The two sides *clasping* is the signature of the working, closed conformation.

**A coil is a genuine energy ramp (ESTABLISHED); whether sequence climbs it is weak (OPEN).** An
α-helix carries a real macrodipole, so axial position is an electrostatic potential — the intuition
that "height on the coil is an energy level" is sound physics. Whether proteins arrange charge to
respect that ramp showed only a weak, non-significant tendency here (+0.23 net drift, p = 0.30).

---

## 7. Results III — continuity, the ±1 height, and observers

**Signed void-line crossings cancel — a continuity law (CONFIRMED, and necessary).** Counting the
chain's crossings of the seam *with direction*, forward and backward crossings match: the total is
1–9 (mean 4.4) but the **net is always within ±1 of zero, in all 8 proteins and from every viewing
angle**. This is continuity checking itself — an unbroken circuit cannot send flow one way without a
matching return. The "return leg" of the verification channel is free.

**The ±1 is a height, hidden from a single angle (CONFIRMED).** Where the net is ±1, the chain's two
termini sit at opposite heights along the cut normal (e.g., LDH +50/−3 Å). The conservation
(|net| ≤ 1) holds from **every** projection angle, but *whether you see* the ±1 depends on the
angle — it vanishes from ~35–40% of directions. The invariant is angle-proof; the height is a
shadow.

**Multiple observers recover the height (CONFIRMED, with a discipline).** Three orthogonal observers
recover a large height offset **100%** of the time (a 3D offset cannot hide from a complete frame),
but cannot manufacture a small one — near-closed chains stay unresolved because there is little
there. **Agreement across observers is the invariant; disagreement between them is the depth** —
stereo vision exactly. The natural committee is a **quaternion**: one real axis (the invariant) plus
three orthogonal imaginary axes (the observer frame).

**Zoom reveals detail at every scale, continuity unbroken, to a finite floor (CONFIRMED).**
Sweeping the crossing-detection resolution from coarse to fine reveals more crossings (a
devil's-staircase gain of steps), while |net| ≤ 1 holds at every scale, bottoming out at a finite
floor set by the residue count. The recursive real+imaginary architecture the author proposes is
formally multiresolution analysis (wavelets), and it terminates at the sequence's granularity.

---

## 8. Results IV — the recursive interface (C) and the convergence point (D)

**C as a graded field is one connected trail, centered, along the cut (CONFIRMED).** Treating the
interface as a graded quality rather than a binary label, the "C" set is a **single connected
component (95–100%)** whose mixture peaks at the center (correlation with distance-from-center −0.43
to −0.68 in every protein) and extends far beyond the ~15% core (up to 66%) as the threshold drops.
It spans 55–72% of the longest axis — the **width of the cut**, not a wire to every tip (the
interface is a 2-D surface through the middle). This "trail" *is* the min-cut surface seen as a
continuous field, and it marks where the fold is weakest.

**Folding creates the seam; it does not fold it out (NEGATIVE / correction).** The intuition that
folding buries or removes the mixed pixels fails on mechanism: the trail is **not** preferentially
buried (corr with exposure −0.06) and is **not** hydrophobic (corr with hydropathy 0.00). C exists
*only because* the domains pack together — folding **creates** the contact seam; most of it ends
interior as a geometric consequence of being a contact, not as an objective of hiding it. The
irreducible ~15% core cannot be removed because it is the glue.

**Each fold makes a C; D is where all the Cs converge (CONFIRMED).** Recursive bisection produces a
fresh interface at every level (C1, C2, C3…), more of them at finer scales. Giving each residue an
**interface-multiplicity** (how many nested interfaces it belongs to), that multiplicity peaks
toward the center (−0.24 to −0.47) and the **bound cofactor sits at elevated multiplicity** (56th–
84th percentile). The cofactor "D" thus has two coincident identities — a **material** one (the
guest molecule) and a **positional** one (the deepest confluence of nested interfaces) — matching
the enzymological fact that active sites sit at the confluence of several structural elements. D is
the **limit of the C series**, not a separate fourth term.

**The convergence is a funnel/cone (CONFIRMED for real sites).** Ray-casting from the ligand apex,
real functional pockets are converging funnels — enclosed on almost every side with a narrow opening
cone (AP5A 0% open, NAD 16%, CoA 23%). Different pockets make **different cone apertures** (0°–58°
across sites), the geometric body of the recursive-C convergence. ("Pyramid power" — energy focused
or reflected by pyramid shape — is pseudoscience and plays no role; the real object is a substrate-
focusing funnel.)

---

## 9. Results V — reading and light (the convergence motif, one scale up)

**Life emits light, and frequency encodes energy (ESTABLISHED).** Ultraweak photon emission
(~1–1000 photons/cm²/s, 200–750 nm) is real, produced when oxidative chemistry relaxes excited
species; bioluminescence and chemiluminescence are the brighter cases. An emitted photon's frequency
equals the energy of the transition (E = hν), so color literally reads the energy released. What is
**not** established — and is actively contested — is whether an organism reads its *own* faint glow
internally; that remains OPEN.

**The reading pocket is a shielded darkroom (CONFIRMED).** The tight woven-core residues are more
buried than average (p < 0.001), 28% fully desolvated — a low-background, low-quench interior
(water, which quenches excited states, is excluded), which would both darken the background and
strengthen any emission. This is the "detector chamber," but a chamber is not yet a detector.

**The eye supplies the missing detector (ESTABLISHED + CONFIRMED geometry).** Rhodopsin's retinal
chromophore is **100% buried** (2.1 of 537 Å² exposed) in a 22-residue pocket; a single photon
isomerizes it (a conformational "collapse") and a G-protein cascade amplifies the signal. The
detector is not fragile but **poised and thermally quiet** (spontaneous isomerization ~ once per
centuries) — sensitive to light, deaf to heat, then amplified. The author's own enzyme set already
contains a chromophore in a buried pocket: **NAD in GAPDH, 84% buried** (NADH absorbs 340 nm,
fluoresces ~460 nm).

**Surrounding composition tunes the reader; pre-filters shape the input (ESTABLISHED).** The three
human cones use identical retinal and peak at ~420/534/564 nm purely by changing the residues around
it; the chromophore sits in concentric **tuning shells** (measured on rhodopsin), and bird/reptile
**oil droplets** pre-filter wavelengths before the reader. "Different cuts → different cones" is real
at the molecular scale (pocket apertures span 0°–58°) and matches the ~eight major **eye optical
types** (pit, pinhole, lens, mirror, apposition, superposition…), all distinguished by cone
geometry and the acuity–sensitivity tradeoff.

**The reader is universal; eyes are one input-instance (ESTABLISHED).** Opsins are GPCRs; smell,
taste, and most hormone/neurotransmitter sensing are GPCRs — one motif (pocket catches input →
conformational change → G-protein → amplified signal), the largest receptor family. The transducer
is **two cones tip-to-tip**: an external pocket catching the input point and an internal point
handing the signal off. This is why eyes re-evolve 40+ times — the reader was already everywhere.

**The C line is a local A/B registrar, but the global layout needs the outer layer (CONFIRMED +
the wall).** Every interface residue sees both faces (100%), with the A-neighbors and B-neighbors on
**opposite sides** (110–131°): each C pixel locally confirms A on one side, B on the other. But a
local reader cannot know where the whole seam *goes* — that is the wall (§10). Local witness; global
agreement.

---

## 10. The wall — what local information cannot do

A single result recurs and bounds the descriptive program. **Sequence → window** (local backbone
state) is readable (~0.54–0.59, above a 0.33 baseline), but **window → seam** is not: even with
*true* local structure, no local descriptor ranks the interdomain boundary above chance — the seam
carries no local signature; it is a pure fact of the global contact web. Correspondingly, no
void-line summary **predicts** the active site better than "guess the center" (baseline 12.1 Å
median error beats every interface/cleft/threading predictor tried). The lesson: **the interface
geometry described in this paper is real, but it is downstream of a nonlocal fact (the web) that
local/sequence information does not determine.** The honest route past the wall is not a cleverer
local reader but an **outer layer** that has learned the web — coevolution, or a protein language
model. §11 shows that route works.

---

## 11. Climbing the wall — the outer layer, demonstrated and made cheap

The structural analysis above is the **inside** of the object; the nonlocal web is an **outer
layer** it cannot derive from itself. (This mirrors, exactly, a separate line of the author's work
in program synthesis, where a structure-only "inside" required wrapping with a learned language
model to become predictive.) The protein equivalent of that outer layer is a **protein language
model** (pLM), which has learned the contact web from evolutionary sequence statistics. We tested it
directly.

**Seam from sequence alone (DEMONSTRATED).** Given only the amino-acid sequence, ESM-2 predicts a
contact map; bisecting that *predicted* web (identically to the true web) recovers the seam:

| protein | L | predicted-contact precision (top-L) | predicted seam vs true seam |
|---|---|---|---|
| 2LZM | 164 | 40% | **94% agree** |
| 4AKE | 214 | 40% | **82%** |
| 1GD1 | 334 | 47% | **89%** |

The seam — the exact quantity §10 shows is *not* locally derivable — is recovered from sequence at
82–94%. Notably the predicted contacts are only ~40% precise, yet the seam still comes out at ~90%,
because the seam is a **coarse global partition**: it needs the overall shape of the web, not every
contact. The nonlocal fact is **robust to contact-prediction noise**, which is why it is
recoverable; a stronger pLM would only sharpen it.

**It runs on modest hardware (DEMONSTRATED).** The **smallest** ESM-2 (8M parameters, CPU) recovers
the seam about as well as the larger model (2LZM 94%, GAPDH 87–89%); the three-domain adenylate
kinase is the honest hard case. Moreover only a small **budget of paths** is needed: the fewest top
predicted contacts that still recover the seam is **~0.2 × L** for clean two-domain folds (41 paths
for 2LZM, 83 for GAPDH) — a fifth of the sequence length and a tiny fraction of the L² map. The path
budget **adapts to complexity** (small for two-domain folds, ~2 × L for the three-domain case),
giving a concrete "size we need" estimator: *count the confident long-range paths the target feature
requires.*

**Count, not bounding area (an honest correction).** A tempting refinement — size the model to the
smallest region enclosing the relevant paths — does **not** work: the needed paths are few but
**spread across the whole map**, because the seam by nature connects distant sequence regions. The
correct knob is the **number** of confident long-range paths, not a compact bounding region.

**Decompose to scale (proposed).** Because the paths are sparse-but-spread, a large target can be
split by the recursive interface hierarchy (§8) and handled by many small models — one per
sub-region's handful of paths — combined by observer agreement (§7). The same structure that
*describes* the protein *parallelizes* the computation.

---

## 12. The honest ledger

**CONFIRMED (measured on n = 8, Fiedler-proxy seam, structure-in):** ligand on the void line; knit
1–7×; matching slot (81% complementary, z = 2.70); ~15% woven core; block-and-rotate (CORE 1.3 Å,
LID 14 Å) with the **hinge axis on the seam (2–5 Å)**; web moves 24%; trails meet when closed;
continuity law (|net| ≤ 1, all angles); ±1 = height; committee recovers large offsets (100%);
devil's-staircase zoom with continuity to a finite floor; C is one connected centered trail;
recursive nested Cs converging on D; funnel pockets; the C-line as a local A/B registrar.

**DEMONSTRATED (working proof-of-concept, small scale):** the seam recovered from sequence alone via
an off-the-shelf pLM (82–94%); recovery robust to ~40% contact noise; recovery with the smallest
(8M) model; a ~0.2×L path budget for two-domain folds; the budget adapting to domain complexity.

**ESTABLISHED (imported, correctly):** active sites in interdomain clefts; induced fit; the
hydrophobic effect; helix macrodipole; ultraweak photon emission and E = hν; single-photon vision
and rhodopsin's mechanism; opsin spectral tuning and cone oil droplets; the ~eight eye optical types
and the acuity–sensitivity tradeoff; GPCRs as the universal receptor motif; multiresolution
analysis; protein language models as contact predictors.

**ANALOGY (real in one domain, mapped — scaffolding, not proof):** DNA = the seam as a
complementary register (for base-pairing only, not read-polarity); RNA = the unbundled peeling
loop; D = a recursive C; the quaternion observer committee; time = the closure angle as reaction
coordinate; "reading = the emitted product/color"; the convergence motif shared from pocket to eye;
the inside/outer-layer correspondence between this work and the author's program-synthesis work.

**OPEN / CONTESTED:** whether an organism reads its own glow internally; whether an ordinary
enzyme's shells are *tuned* to read light versus arranged for catalysis; the detector/amplifier
beside a buried chromophore; whether sequence deliberately climbs the helix ramp; whether the full
geometry (trail, D, funnel) survives being computed on a *predicted* rather than a true structure.

**NEGATIVE (tested and refuted — settled):** "read one side at a time" (antiparallel: no; exposure
asymmetry: no — the register is symmetric); "light from 3 directions" (it is 2 walls); "folding
folds the C pixels out" (folding *creates* the seam; C is not hydrophobic); "size the model to the
smallest enclosing region" (paths are sparse but long-range — size by count); window → seam from the
local alphabet; the void line as an active-site predictor beating the center. Pseudoscience kept
out: pyramid "energy," and the strong biophoton-communication claim.

**Meta:** **calmodulin is the floor** — the minimal exception in nearly every test (one crossing,
exposed hinge, no dark core, flat staircase, trails that never meet). Its consistency as a negative
control is itself weak evidence the measures track something real.

---

## 13. Discussion — the one motif, and the way past its limit

Stripped to a sentence: **a two-domain fold is organized around its seam, the same
convergence-to-a-point motif appears at every scale of it, and the one thing local structure cannot
supply — the global web — is exactly what a learned outer layer restores.** The seam is a connected
graded trail; that trail centers on a point; the point is where nested interfaces converge and where
the cofactor binds; the pocket around it is a funnel; the funnel is a molecular instance of the
converging reader that, one scale up, is a photoreceptor, and one family over, is every GPCR sense.
The recursion is not decoration — it is the same object (knit/weave, core/trail, invariant/shadow,
C/D, pocket/eye) seen at different magnifications, exactly as multiresolution analysis would predict,
and terminating at the finite granularity the sequence provides.

Against this stands one persistent limit, and its resolution. Everything local — windows, slots, the
per-residue registrar, a single observer's shadow — is *cheap and real but incomplete*. The one
thing that is not local, the global contact web, is what actually fixes the fold, the seam's route,
and the site. It is not derivable from the inside; it must be **supplied by an outer layer** that
learned it — and §11 shows an off-the-shelf pLM does supply it, cheaply, recovering the seam from
sequence at ~90% with the smallest model and a fifth of the paths.

---

## 14. Limitations

The sample is eight curated single-chain two-domain enzymes; the seam is a Fiedler proxy, not a
curated minimum-cut, and it mis-splits 3+-domain proteins. Most structural results are **descriptive
and structure-in**: they characterize folded coordinates, they do not by themselves predict fold,
seam, or site from sequence. §11 lifts this only for the **seam** (a coarse feature) and only as a
small proof-of-concept. Several "confirmations" are moderate in effect size; a few ligand analyses
are sensitive to which heteroatom is treated as the ligand. The biological and physical sections
lean on established literature, not on new measurement; the cross-domain mappings are analogies and
are labeled so.

---

## 15. Open questions and next steps

1. **Wrap the whole structure, not just the contacts.** Predict full 3D coordinates from sequence
   (ESMFold / AlphaFold) and re-run the *entire* analysis — trail, convergence point D, funnel — on
   the **predicted** structure.
2. **Broaden and quantify.** Repeat every CONFIRMED result on a large curated two-domain benchmark
   with a real minimum-cut boundary and a stronger pLM; report effect sizes with confidence
   intervals.
3. **The detector question.** Search structurally for a poised switch adjacent to a buried
   chromophore — the missing piece between a darkroom and a reader.
4. **Formalize the recursion and the sizing.** Write the recursive quaternion multiresolution
   decomposition explicitly; validate the path-count capacity budget as a predictor of model size.
5. **Decomposed inference.** Implement the split-and-combine scheme (small models per sub-region,
   combined by observer agreement) and benchmark accuracy-vs-hardware.
6. **Tuning as a measurable prediction.** Ask whether pocket cone-aperture and shell composition
   predict any functional axis.

---

## Appendix — reproducibility

Each result is produced by a named script (Python 3, biotite/NumPy/SciPy, plus PyTorch + `fair-esm`
for §11). Structures are public RCSB PDB entries; the ESM-2 weights are public. In this repository,
the recursion/wall-climb code is in `code/` (`pipeline.py`, `test_c.py`, `test_d.py`); the extended
folding-thread tests (deformation, floors, blanket, sequence budget) are `code/test_*.py`.

*End of working draft. The strongest, most defensible core is §§5–8 and §13 (the seam architecture
and the convergence motif); §11 (climbing the wall with a pLM) is a small but genuine
proof-of-concept that turns §10 from a dead end into a resolved limit.*
