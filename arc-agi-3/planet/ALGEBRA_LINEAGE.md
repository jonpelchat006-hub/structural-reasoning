# Algebra lineage and first working bridge

Local review and offline experiments, 2026-09-07. This is a source map and a
tested starting point, not a claim that every historical theory is established.
The review sampled the named projects and their linked notes, not every file on
the computer. Existing detailed cube records remain authoritative.

## Where the ideas connect

| Source | Concrete connection | What remains distinct |
| --- | --- | --- |
| [Failure learning](<C:/Users/GamerTech/Desktop/Vesica AI/Learning/failure_learning.py>) | Store failures and seek boundaries of known behavior. | A learning heuristic, not a zero-divisor calculation. |
| [Quaternion observer](<C:/Users/GamerTech/Desktop/Vesica AI/Consciousness/quaternion_consciousness.py>) | One observer component alongside three other axes. | Conceptual/prototype mapping; no demonstrated consciousness or ARC advantage. |
| [Incidence geometry](D:/shovelcat-colony/erdos-incidence-geometry/README.md) | Separate abstract incidence structure from realizability constraints. | An abstract pattern need not have the desired planar realization. |
| [Orchard 11 construction](D:/shovelcat-colony/Shovelcat/erdos-Fk/ORCHARD_11_16_SOLVED.md) and [verifier](D:/shovelcat-colony/Shovelcat/erdos-Fk/verify_11.py) | Expand the coordinate field to represent a successful construction. | This construction uses Q(sqrt(5)); its verification alone does not prove rational realizations impossible. |
| [Void-anchor notes](D:/shovelcat-colony/Shovelcat/erdos-Fk/VOID_ANCHOR_NOTES.md) | Use constraints and obstructions as construction targets. | Search observations and geometric certificates require separate treatment. |
| [Sphere generator](D:/shovelcat-colony/arc-proposer/SPHERE_GENERATOR.md) and [tests](D:/shovelcat-colony/arc-proposer/SPHERE_GENERATOR_TEST.md) | Explicit Cayley-Dickson ladder and sedenion annihilating directions as void anchors. | The notes themselves distinguish the orchard field extension from algebra doubling. |
| [Codon DSL](D:/shovelcat-colony/arc-slice/src/codon.ts) | Group different programs with the same behavior; retain useful survivors. | Behavioral equivalence is not sedenion multiplication. |
| [Folding outer slot](<C:/Users/GamerTech/Desktop/Vesica AI/AI Detector/FOLDING_OUTER_SLOT.md>) and [void-line draw](<C:/Users/GamerTech/Desktop/Vesica AI/AI Detector/FOLDING_VOID_LINE_DRAW.md>) | Preserve disagreement between views and investigate seams. | Spectral/segmentation boundaries are not automatically algebraic annihilators. |
| [Void search](<C:/Users/GamerTech/Desktop/Vesica AI/AI Detector/planet/voidsearch.py>) | Similarity graph plus Laplacian/Fiedler cut locates document seams. | This implementation uses graph spectra, not sedenions. |
| [ARC planet](<C:/Users/GamerTech/Desktop/Vesica AI/AI Detector/ARC_PLANET.md>), [diagonals](<C:/Users/GamerTech/Desktop/Vesica AI/AI Detector/planet/diagonal.py>), [views](<C:/Users/GamerTech/Desktop/Vesica AI/AI Detector/planet/views.py>) | Context, effect, and verification become connected records viewed from different directions. | Compressed coordinates do not replace the relations, observations, or experiment history. |

My interpretation of the recurring idea: retain the boundary where a
representation fails, add the missing context or representation, and test the
new connection. That is a useful research program. It does not require every
kind of boundary to be the same mathematical object.

The orchard verifier was rerun successfully with Python's UTF-8 output mode:
11 points, 16 three-point lines, no four-or-more-point lines. That checks the
construction, not an independent upper-bound proof of optimality. The first
run reached the same checks but failed printing an approximation symbol in
the default Windows console encoding; no source change was needed.

## Implemented now

- `cayley.py`: dimensions 1, 2, 4, 8, 16, 32; multiplication, conjugation,
  operand-preserving product reports, numerical left/right annihilator bases,
  and the historical finite doublet search. It agrees with existing
  `quat.qmul` and `quat.omul`.
- `cube_memory.py`: a versioned 16-channel field, evidence-rate helper with
  sample counts, and a diagnostic for old quaternion signatures that hide
  distinct new records.
- `views.py`: builds `self.s` alongside unchanged `self.q`, includes the
  collision diagnostic in collapse statistics, and saves `_s.npy` plus channel
  metadata alongside the existing JSON and `_q.npy` outputs.
- `algebra_audit.py`: reconstructs saved views in memory and audits algebra
  and adjacent records without changing recordings or calling a game API.
- `test_algebra_memory.py`: offline regression tests for the algebra,
  evidence distinctions, and live-view/save/offline-audit integration.

There is no new action-selection rule, confidence promotion, model training,
or live-game benchmark. The evidence-rate helper is available for future
selection logic; it is not yet wired into the planner.

### Explicit cube coordinates

The field is an experimental coordinate assignment, not a learned algebra.
It is four four-component blocks (also two eight-component halves):

| Indices | Channels |
| --- | --- |
| 0-3 | Up, down, left, right border observations separately: -1 refusal, 0 unknown, +1 pass. |
| 4-7 | Fired with condition, fired without, silent with, silent without: aggregated raw counts. |
| 8-11 | Diagonal-foot count, back-reference count, owner-present flag, water. |
| 12-15 | Up, down, left, right trail flags. |

Unlike the old summary, opposite directions cannot cancel each other, and
silent-with observations cannot disappear from the success evidence. But this
is still not lossless memory: per-pin identity, conditions, targets, object IDs,
and other geometry stay in the detailed dictionaries. Counts are not all on
comparable scales. Multiplication mixes these chosen channels and has no
established causal interpretation. It also treats channel zero as the scalar
coordinate; that is a convention to test, not an intrinsic property of borders.

## What the checks actually found

The historical search family is exactly `e_i + e_j`, with
`1 <= i < j < dimension`. Pairs are ordered and products use this convention:

`(a,b)(c,d) = (ac - conjugate(d)b, da + b conjugate(c))`.

| Dimension | Doublets | Ordered zero-product pairs | Participating doublets |
| --- | ---: | ---: | ---: |
| Quaternion, 4 | 3 | 0 | 0 |
| Octonion, 8 | 21 | 0 | 0 |
| Sedenion, 16 | 105 | 84 | 42 |

Each participating sedenion doublet has two partners in this family. A concrete
witness is `(e1 + e10) * (e5 + e14) = 0`, with both operand norms sqrt(2).
For `e1 + e10`, the numerical right-annihilator has dimension four; reported
unit-vector residuals are below 5e-16. These are directions in algebra space,
not yet identified lines or actions in an ARC board.

The finite search reproduces the old note's numbers; it does not enumerate all
zero divisors. Integer reports are exact only within int64 arithmetic range.
Floating zero products are separately labeled numerical, not exact witnesses;
near-zero products and numerical kernel directions need tolerance checks.

The standard algebra supports zero divisors appearing at dimension 16, not a
universal rule that every failed search needs another doubling. Also, do not
equate zero divisors with all nonzero elements lacking two-sided inverses:
nonassociativity prevents the usual cancellation argument. See
[Baez's Cayley-Dickson construction](https://math.ucr.edu/home/baez/octonions/node5.html).

Saved ARC results, from [the audit report](D:/planet/eye/algebra_audit_20260907_codex.json):

| Snapshot | Old signatures hiding distinct records | Tested nonzero neighbor pairs | Near-zero products |
| --- | ---: | ---: | ---: |
| views_ls20_L1.json | 15 | 2486 | 0 |
| views_ls20_L2.json | 11 | 2432 | 0 |
| views_ls20.json | 15 | 2798 | 0 |

Products use right/down neighbors, the unlifted 16-channel assignment, unit
normalization, and tolerance 1e-12. Minimum relative residuals were about
0.977, 0.882, and 0.856: not even near annihilation in these tests.
Signature collisions include disconnected locations and are not proof of
incorrect object grouping. The immediate demonstrated value is retaining more
distinctions, not a solver gain or an observed algebraic void in ARC.

## Next useful experiments

1. Use the retained with/without sample counts to select a missing test for a
   diagonal hypothesis. A single firing with no negative trial is untested
   contrast, not confirmed causality. Start on replayed observations.
2. Keep a compositional record `(left, operator, right, product, evidence)`;
   never replace two nonempty operands with just their zero product. This
   connects the old void-anchor idea directly to recoverable memory.
3. Compare matched-budget runs: existing planner; richer evidence only;
   richer evidence plus an explicitly defined algebra proposal rule. Measure
   predictions, levels, presses, and time. Include alternate channel maps to
   detect coordinate artifacts before attributing gains to sedenions.
4. Separate two kinds of representation repair: missing variables/context
   (the orchard field-extension lesson) versus composition failures (where
   a richer algebra might help). Let counterexamples choose the repair.

## Reproduce

From PowerShell:

```powershell
Set-Location -LiteralPath 'C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet'
python -X utf8 -B -W error::ResourceWarning -m unittest test_algebra_memory -v
python -X utf8 -B algebra_audit.py --views D:\planet\eye\views_ls20_L1.json D:\planet\eye\views_ls20_L2.json D:\planet\eye\views_ls20.json
python -X utf8 -B 'D:\shovelcat-colony\Shovelcat\erdos-Fk\verify_11.py'
```

The audit prints JSON unless `--output` is supplied. An output path must be new:
the tool refuses to overwrite existing reports. Existing recordings, route
logic, and user modifications were preserved. New `_s.npy` files are produced
only when the regular view-saving path runs.
