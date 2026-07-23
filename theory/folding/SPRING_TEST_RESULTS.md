# Spring Test — Results [built, run — WORKS, but on the easy target]

*First measurable protein result. Tests whether Jonathan's Sphere-Generator ribbon/frame operator (a framed ribbon threaded outward, a stored twist = unit quaternion, oriented placement) reproduces a real α-helix backbone.*

## Setup (non-circular by construction)
`thread_ribbon()` places each residue's Cα by advancing a frame a fixed rise along the helix axis and rotating it by a stored twist quaternion (a screw motion), recording position + orientation + twist per residue. Parameters are **canonical, NOT fit to the target** (100°/residue, 1.5 Å rise, 2.3 Å Cα radius — textbook α-helix screw); the generator never sees the answer. Ground truth: longest α-helix in sperm-whale myoglobin (1MBN, res 126–148, 23 residues). Score: Kabsch superposition, Cα RMSD.

## Result — sub-angstrom
rise/residue 1.50 Å (real 1.59), residues/turn 3.60 (real 3.62), Cα radius 2.30 Å (real 2.26), **Cα RMSD 0.585 Å**. The operator places a real helix correctly — "it's a spring, not a block" validated in angstroms.

## Honest reading
Confirms the placement operator is real and correctly implemented (oriented-atom + twist-record output maps onto real residue-frame representation). Does NOT show predicting *which* structure a sequence folds to, whole-protein assembly, or beating AlphaFold — proven on the single easiest target (a helix is *supposed* to be a clean screw). The "but" lives in the loops/turns (where the screw breaks), secondary-structure assignment, and tertiary packing — the gap an energy function must model. Next bricks: β-strand placement, the turn between two helices, then a scoring function validated by decoy discrimination (never score yourself on the answer you fit).

*Artifacts: `spring_test.py`, `spring_test.png`, `helix_ours.pdb`, `helix_real.pdb`.*
