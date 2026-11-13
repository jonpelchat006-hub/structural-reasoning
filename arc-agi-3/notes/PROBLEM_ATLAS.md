# Problem atlas: the eight Lean problems and ARC in the ring frame (Oct 20, 2026)

Jonathan, Oct 20:
- *"so then we have to figure out what goes on those lines and what can enter those slots? should we just plug it into mika? or see what all the problems are doing in this framework?"*
- Agreed plan: map the problems first, test the sharpest prediction, and only then give Mika the pieces that earn a job.

The frame comes from `CORE_POINTS_AND_MISFIT_RINGS.md`. Read operationally:

| Frame part | In a computation |
|---|---|
| **Line** | the state passed from one step to the next (the thin waist) |
| **Slots** | the positions values fill (lanes, digits, cells) |
| **Core** | what is proved once and then supports every step |
| **Switches** | what the input decides along the way |
| **Levels** | the symmetry used: none, a half turn (order 2) or a third turn (order 3) |

## The eight Lean problems

Costs are local, from the v4 notes and later passes. About 215k per case (1.29M per problem) is fixed overhead that everyone pays.

| Problem | Line | Slots | Core | Switches | Symmetry used | Cost now | What the frame adds |
|---|---|---|---|---|---|---|---|
| partition | the whole count table as one number | one digit per count | no-carry lane bound | none | **half turn**: conjugation (Durfee square core with two mirror arms) | 1.571M (near the floor) | retrodicts the Durfee trick; nothing new |
| primecount | the sieve as one number | one slot per integer | Mathlib prime facts | sieving primes ≤ √N | the 6k±1 wheel removes the 2- and 3-structure (6 = 2·3, the two core orders) | 1.626M (near the floor) | retrodicts the wheel; nothing new |
| mertens | packed Möbius lanes | one slot per integer | Möbius facts | sieving primes | same 6k±1 wheel | 2.327M (near the floor) | same |
| fib | the pair (F, L) | none: two huge numbers | Cassini (det = −1), x² = x + 1 | the bits of n | **the golden line itself**: L and √5·F are the line's two sides (φⁿ ± ψⁿ, feet φ and −1/φ) | 6.89M (v8; the final product is the floor) | retrodicts (F, L); nothing new |
| ca-rule110 | the 256-cell row | one bit per cell | per-lane rule lemma | step count | none exists (rule 110 has no mirror or complement symmetry) | 3.723M | consistent: nothing to fold |
| sha256 | 8 words + schedule window | none pay (2 lanes measured −1.5%) | rfl against structured rounds | none | none (by design) | 10.24B | consistent: no structural lever. The 9% gap to 1st (Oct 4 board) is per-operation overhead |
| permanent | the subset-DP vector | one lane per column subset, trimmed | lane bound or run-time check | 3 seeded ones per row | row/column relabeling (used); **transpose, the mirror (unused)** | 18.17M | open lead (Test 2) |
| polydisc | the two polynomials | one lane per coefficient (v8, D1/D3) | **missing**: exactness is paid for per step | degree drops: normal = every quotient degree 1 (the all-1 "golden" string); bigger = fallback | none | 1,205M (D5 is 92%) | **prove the structure once** (Test 1) |

**Reading.**
- On four problems, the frame only re-finds tricks already in the entries (retrodiction): partition, primecount, mertens and fib. All four are near their floors.
- On two it correctly says there is nothing structural to gain: sha256 and rule 110.
- It points at two unused levers, polydisc's core and permanent's mirror, and both were tested.

## Test 1: polydisc D5, prove the structure once

The low-part method from Oct 19 keeps only the bits each step needs (§ in `LEAN_POLYDISC_PACKED.md`). It is sound only if two things are proved instead of checked:
1. every division is exact;
2. a width bound, fixed in advance.

**Step 1: the PRS is the determinant structure.** Each PRS polynomial equals ±(the subresultant determinant): 223 of 223 random small cases matched exactly (`subres_check.py`). So exactness and bounds both follow from determinant facts.

**Step 2: is there a provable bound tight enough to keep the saving?** Bounds are computed from the spec's coefficient-width limits only, so an impl can fix them in advance per band. Two D5 inputs were priced with Lean's GMP:

| Bound | Width vs actual (S_0 … S_22) | D5 GMP per case |
|---|---|---|
| Today: full numerators + exact division | — | 469M |
| Low part, measured widths (not sound) | 1.00 | 280.4M |
| Low part, column-sum (Hadamard-type) bound | 1.04–1.80× | 471.4M: no gain |
| **Low part, permutation bound** | **1.002–1.008×** | **281.6M** |

The permutation bound:
- It states `|det| ≤ k! × (the largest single permutation product)`.
- The largest product is found offline by a max-weight assignment on the width limits.
- The `k!` term costs at most about 200 bits out of 80k.

**Result.**
- The provable bound keeps the saving: about −187M per D5 case, plus about 7M of extra kernel operations.
- Polydisc would go from 1,205M to about 845M, roughly −30%.

**What a real v9 needs in core Lean** (no Mathlib):
1. integer determinants;
2. PRS step = ±(subresultant determinant), which gives exactness in the normal case;
3. Leibniz's formula for `|det| ≤ k!·max`;
4. dual potentials certifying the offline maximum, which is an easy proof once the potentials are given;
5. widths from the spec's construction;
6. odd-part handling for `dm` (the 2-adic inverse needs an odd divisor).

Abnormal degrees stay detectable: with the bound, a leading coefficient is zero exactly when its low part is zero. Item 2 is the big formal job.

Scripts are in `research/polydisc_lowpart/` on the PC.

**Done (Oct 20, v9).** All six items are proved in core Lean, and the run is built: `LEAN_POLYDISC_V9.md`.
- D5: 557M → 300M per case (−46%).
- polydisc: 1,205M → about 692M (−43%).
- The local judge accepts it.

## Test 2: permanent, use the mirror

`perm(A) = perm(Aᵀ)`. Exact DP state counts (the submission's direction, 200 seeds each, `transpose.py`):

| d | Transpose / A, median | Range | Transpose smaller |
|---|---|---|---|
| 12 | 0.88 | 0.10–8.9 | 114 of 200 |
| 16 | 1.07 | 0.07–12.4 | 96 of 200 |

- The mirror changes the DP size by up to 13× either way per seed, but with no consistent winner.
- Using it would need a cheap per-seed predictor, priced against the v6 trimming model.
- This is an open lead, not a result.

## ARC: the frame's levels against what the solver already solves

All ARC-1 tasks, sorted by what the train pairs do. Solved lists are `verified_solved.txt` (81 training tasks) and `verified_eval.txt` (34 eval tasks), read from `arc-slice`.

| Level | Training tasks | Solved | Eval tasks | Solved |
|---|---|---|---|---|
| A. Core move (output = a turn or flip of the input) | 7 | **7 (100%)** | 0 | — |
| B. Lands on a symmetric state (output more symmetric than input) | 51 | 15 (29%) | 36 | **11 (31%)** |
| C. Fills empty slots only (same size, only background cells change) | **122** | 15 (12%) | **99** | **1 (1%)** |
| D. Recolors or erases only | 34 | 7 (21%) | 50 | 2 (4%) |
| E. Same size, mixed changes | 85 | 11 (13%) | 106 | 4 (4%) |
| F. Output smaller (reads out a part) | 74 | 21 (28%) | 76 | 10 (13%) |
| G. Output larger (expands) | 26 | 5 (19%) | 32 | 5 (16%) |

Level B split by size:

| Part of B | Training | Eval |
|---|---|---|
| Same size (completing a symmetry) | 6/14 | 4/15 |
| Tiny outputs (≤ 3×3) | 0/14 | 4/10 |
| Other size changes | 9/23 | 3/11 |

**Reading.**
- Core moves are fully solved.
- Landings on a symmetric state are the one level that holds up on held-out tasks: 29% on training, 31% on eval. Every other level drops 1.2× to 12×.
- Slot filling is the biggest class on both sets and the weakest on eval: 1 solve in 99. The solver does not know what can enter a slot, which is exactly Jonathan's question.
- Every ARC grid is a square lattice, the square torus at the half-turn point. Turns and flips are that point's own symmetries, so no third-turn (120°) structure can occur in grid geometry.

## Verdict and next steps

- **Lean.** The frame's biggest lever was real: the D5 core. It is now proved and built (v9), at −43% of polydisc, more than the −30% estimate. The mirror lead for permanent needs a predictor.
- **Mika.** The first tool worth giving her is a **slot filler**: rules for what may enter an empty cell, learned from the pairs and checked on all of them. That is where the solver is blind, and it is the largest class.
- **Labels.** The mapping is a labeling. The tests (the bound pricing, the state counts and the class solve rates) are the measured part.
